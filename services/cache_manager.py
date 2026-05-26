"""
In-memory cache manager with periodic disk persistence.
Provides fast lookups for duplicate document detection.

AUTOMATIC CACHE INVALIDATION:
- Cache version includes hash of critical code files
- When code changes, cache is automatically invalidated
- No manual cache clearing needed after updates
"""
import asyncio
import json
import logging
import os
import time
import hashlib
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Files to monitor for cache invalidation
CRITICAL_FILES = [
    "services/llm_service.py",
    "services/post_processing.py",
    "services/document_service.py",
    "services/ocr_service.py",
    "services/normalizer.py",  # NEW: Schema refactor
    "models/schemas.py",  # NEW: Schema refactor
]


def _compute_code_hash() -> str:
    """
    Compute hash of critical code files.
    When these files change, cache should be invalidated.
    """
    hasher = hashlib.sha256()
    
    for file_path in CRITICAL_FILES:
        try:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    hasher.update(f.read())
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
    
    return hasher.hexdigest()[:12]


# Cache version includes code hash for automatic invalidation
CODE_HASH = _compute_code_hash()
CACHE_VERSION = f"3.0-schema-refactor-{CODE_HASH}"

logger.info(f"Cache version: {CACHE_VERSION}")


class CacheManager:
    """
    LRU cache with in-memory storage and periodic disk sync.
    Thread-safe for concurrent access.
    """
    
    def __init__(
        self,
        cache_dir: str = "cache",
        max_size: int = 1000,
        sync_interval: int = 60,
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache persistence
            max_size: Maximum number of cached results
            sync_interval: Seconds between disk syncs
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.sync_interval = sync_interval
        
        # In-memory LRU cache: {file_hash: (result_dict, timestamp)}
        self._cache: OrderedDict[str, tuple[Dict, float]] = OrderedDict()
        
        # Cache statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Sync task
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache from disk
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load cache index from disk on startup."""
        index_file = self.cache_dir / "cache_index.json"
        
        if not index_file.exists():
            logger.info("No existing cache index found. Starting fresh.")
            return
        
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
            
            loaded = 0
            for file_hash, entry in index.items():
                result_file = self.cache_dir / f"{file_hash}.json"
                if result_file.exists():
                    with open(result_file, "r", encoding="utf-8") as rf:
                        result = json.load(rf)
                    self._cache[file_hash] = (result, entry["timestamp"])
                    loaded += 1
            
            logger.info(f"Loaded {loaded} cached results from disk.")
            
        except Exception as exc:
            logger.error(f"Failed to load cache from disk: {exc}")
    
    async def _sync_to_disk(self):
        """Periodically sync cache to disk."""
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval)
                
                # Build index
                index = {}
                for file_hash, (result, timestamp) in self._cache.items():
                    index[file_hash] = {
                        "timestamp": timestamp,
                        "filename": result.get("filename", "unknown"),
                    }
                
                # Write index
                index_file = self.cache_dir / "cache_index.json"
                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(index, f, indent=2)
                
                # Write individual result files
                for file_hash, (result, _) in self._cache.items():
                    result_file = self.cache_dir / f"{file_hash}.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Synced {len(self._cache)} cache entries to disk.")
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Cache sync error: {exc}")
    
    async def start(self):
        """Start the cache manager background sync task."""
        if self._running:
            return
        
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_to_disk())
        logger.info("Cache manager started.")
    
    async def stop(self):
        """Stop the cache manager and perform final sync."""
        if not self._running:
            return
        
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        # Final sync
        try:
            index = {}
            for file_hash, (result, timestamp) in self._cache.items():
                index[file_hash] = {
                    "timestamp": timestamp,
                    "filename": result.get("filename", "unknown"),
                }
            
            index_file = self.cache_dir / "cache_index.json"
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
            
            for file_hash, (result, _) in self._cache.items():
                result_file = self.cache_dir / f"{file_hash}.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info("Cache manager stopped. Final sync completed.")
        except Exception as exc:
            logger.error(f"Final cache sync error: {exc}")
    
    def get(self, file_hash: str) -> Optional[Dict]:
        """
        Get cached result by file hash.
        Returns None if not found.
        """
        if file_hash in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(file_hash)
            result, _ = self._cache[file_hash]
            cached_version = result.get("_cache_version")
            if cached_version != CACHE_VERSION:
                logger.warning(
                    f"Cache INVALIDATED for hash {file_hash}: "
                    f"cached version '{cached_version}' != current version '{CACHE_VERSION}'. "
                    f"Code has changed - reprocessing document."
                )
                self.delete(file_hash)
                self._misses += 1
                return None
            self._hits += 1
            logger.info(f"Cache HIT for hash {file_hash} (version {CACHE_VERSION})")
            return result
        
        self._misses += 1
        logger.info(f"Cache MISS for hash {file_hash}")
        return None
    
    def put(self, file_hash: str, result: Dict):
        """
        Store result in cache.
        Evicts oldest entry if cache is full.
        """
        result = dict(result)
        result["_cache_version"] = CACHE_VERSION

        # Remove if already exists (will re-add at end)
        if file_hash in self._cache:
            del self._cache[file_hash]
        
        # Add to cache
        self._cache[file_hash] = (result, time.time())
        
        # Evict oldest if over limit
        while len(self._cache) > self.max_size:
            oldest_hash, _ = self._cache.popitem(last=False)
            self._evictions += 1
            logger.debug(f"Evicted cache entry: {oldest_hash}")
            
            # Delete file from disk
            try:
                result_file = self.cache_dir / f"{oldest_hash}.json"
                if result_file.exists():
                    result_file.unlink()
            except Exception as exc:
                logger.warning(f"Failed to delete evicted cache file: {exc}")
        
        logger.debug(f"Cached result for hash {file_hash}")

    def delete(self, file_hash: str):
        """Delete a cache entry from memory and disk."""
        if file_hash in self._cache:
            del self._cache[file_hash]

        try:
            result_file = self.cache_dir / f"{file_hash}.json"
            if result_file.exists():
                result_file.unlink()
        except Exception as exc:
            logger.warning(f"Failed to delete cache file {file_hash}: {exc}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate_percent": round(hit_rate, 2),
        }
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info("Cache cleared.")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        cache_dir = os.getenv("CACHE_DIR", "cache")
        max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))
        sync_interval = int(os.getenv("CACHE_SYNC_INTERVAL", "60"))
        
        _cache_manager = CacheManager(
            cache_dir=cache_dir,
            max_size=max_size,
            sync_interval=sync_interval,
        )
    return _cache_manager
