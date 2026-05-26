"""
Document Data Normalizer

Purpose: Clean and normalize LLM/OCR output BEFORE schema validation.
Integrated with OOPS Strategy pattern using the DocumentProcessorFactory.
Optimized with DSA Memoization (LRU Cache) for expensive string sanitizations.
"""

import re
import unicodedata
import logging
from typing import Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================
# EMPTY VALUE PATTERNS
# ============================================================

EMPTY_PATTERNS = {
    "",
    "   ",
    "N/A",
    "n/a",
    "NA",
    "null",
    "NULL",
    "None",
    "NONE",
    "-",
    "--",
    "___",
}


# ============================================================
# CACHED STRING SANITIZER (DSA MEMOIZATION OPTIMIZATION)
# ============================================================

@lru_cache(maxsize=2048)
def _sanitize_string_cached(value_str: str) -> Optional[str]:
    """
    LRU-cached core string cleaning utility.
    Speeds up repetitive regex and unicode normalization scans.
    """
    # Check empty patterns in O(1) hashing
    if value_str in EMPTY_PATTERNS:
        return None
    
    # Unicode normalization (NFC form)
    try:
        cleaned = unicodedata.normalize('NFC', value_str)
    except Exception:
        cleaned = value_str
    
    # Remove zero-width spaces and invisible characters
    cleaned = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', cleaned)
    
    # Normalize whitespace (multiple spaces → single space)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


# ============================================================
# UTILITY CLEANERS
# ============================================================

def normalize_string(value: Any) -> Optional[str]:
    """
    Normalize string values with internal memoization.
    """
    if value is None:
        return None
    
    # Convert non-string types safely
    if not isinstance(value, str):
        value_str = str(value).strip()
    else:
        value_str = value.strip()
        
    return _sanitize_string_cached(value_str)


def normalize_list(value: Any) -> Any:
    """Normalize lists by flattening single items or joining string lists."""
    if not isinstance(value, list):
        return value
    if not value:
        return None
    if len(value) == 1:
        return value[0]
    
    if all(isinstance(item, str) for item in value):
        joined = ' '.join(item.strip() for item in value if item.strip())
        return normalize_string(joined)
    
    return value


def normalize_nested_object(value: Any) -> Any:
    """Flatten simple nested JSON structures (e.g. name objects)."""
    if not isinstance(value, dict):
        return value
    if not value:
        return None
    
    if len(value) == 1 and "value" in value:
        return value["value"]
    
    if all(k in ["first", "last", middle_key] for middle_key in ["middle"] for k in value.keys()):
        parts = []
        if "first" in value and value["first"]:
            parts.append(str(value["first"]))
        if "middle" in value and value["middle"]:
            parts.append(str(value["middle"]))
        if "last" in value and value["last"]:
            parts.append(str(value["last"]))
        return ' '.join(parts) if parts else None
    
    return value


def normalize_number(value: Any) -> Optional[float]:
    """Normalize numeric values (e.g., stripping currencies, formatting symbols)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value_str = value.strip()
        value_str = re.sub(r'[₹$€£¥]', '', value_str)
        value_str = value_str.replace(',', '').replace(' ', '')
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Could not convert to number: {value}")
            return None
    return None


# ============================================================
# MAIN ENTRY POINT (OOP DELEGATION)
# ============================================================

def normalize_document_data(document_type: str, data: dict) -> dict:
    """
    Main entry point for document data normalization.
    Uses the DocumentProcessorFactory to resolve and execute the clean strategy.
    
    Args:
        document_type: Type of document (aadhaar, pan, etc.)
        data: Raw extracted data dict
        
    Returns:
        Cleaned and normalized dictionary
    """
    from services.processors import DocumentProcessorFactory
    
    # Resolve strategy from our factory in O(1) hash lookups
    processor = DocumentProcessorFactory.get_processor(document_type)
    return processor.normalize(data)


def is_empty_value(value: Any) -> bool:
    """Check if value is empty/null."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in EMPTY_PATTERNS
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def clean_dict(data: dict) -> dict:
    """Remove empty/null keys from dictionary."""
    return {k: v for k, v in data.items() if not is_empty_value(v)}
