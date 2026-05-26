"""
Batch upload endpoint for processing multiple documents concurrently.
"""
import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from models.task_schemas import BatchUploadResponse, TaskCreateResponse, TaskStatus
from services.cache_manager import get_cache_manager
from services.task_queue import get_task_queue

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_BATCH_SIZE = 20


@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload(files: List[UploadFile] = File(...)):
    """
    Upload multiple documents for concurrent processing.
    
    Accepts up to 20 files. Each file is validated and queued for processing.
    Returns an array of task IDs for tracking progress.
    
    Query parameters:
    - files: List of files to upload (max 20)
    
    Returns:
    - total_files: Number of files submitted
    - accepted: Number of files accepted for processing
    - rejected: Number of files rejected (validation failed)
    - tasks: Array of TaskCreateResponse objects
    - errors: Array of error messages for rejected files
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum batch size is {MAX_BATCH_SIZE}"
        )
    
    cache_manager = get_cache_manager()
    task_queue = get_task_queue()
    
    tasks = []
    errors = []
    accepted = 0
    rejected = 0
    
    for idx, file in enumerate(files):
        try:
            # Validate filename
            if not file.filename:
                errors.append(f"File {idx + 1}: Missing filename")
                rejected += 1
                continue
            
            filename = file.filename
            extension = os.path.splitext(filename)[1].lower()
            
            # Validate file type
            if extension not in ALLOWED_EXTENSIONS:
                errors.append(
                    f"File {idx + 1} ({filename}): Unsupported file type. "
                    f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                )
                rejected += 1
                continue
            
            # Read file content
            file_content = await file.read()
            
            # Validate file size
            if len(file_content) > MAX_FILE_SIZE:
                errors.append(
                    f"File {idx + 1} ({filename}): File too large. "
                    f"Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
                )
                rejected += 1
                continue
            
            # Compute file hash
            import hashlib
            hasher = hashlib.sha256()
            hasher.update(file_content)
            file_hash = hasher.hexdigest()[:12]
            
            # Check cache
            cached_result = cache_manager.get(file_hash)
            
            if cached_result:
                # File already processed - return cached result immediately
                logger.info(f"Cache HIT for {filename} (hash: {file_hash})")
                tasks.append(
                    TaskCreateResponse(
                        task_id=file_hash,  # Use hash as task_id for cached results
                        status=TaskStatus.COMPLETED,
                        message=f"Document already processed (cached)",
                        cached=True,
                    )
                )
                accepted += 1
            else:
                # New file - create task
                # Save file temporarily
                upload_dir = os.getenv("UPLOAD_DIR", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, f"{file_hash}_{filename}")
                
                with open(file_path, "wb") as f:
                    f.write(file_content)
                
                # Create task
                task_id = await task_queue.create_task(filename, file_hash)
                
                logger.info(f"Created task {task_id} for {filename}")
                tasks.append(
                    TaskCreateResponse(
                        task_id=task_id,
                        status=TaskStatus.PENDING,
                        message=f"Document queued for processing",
                        cached=False,
                    )
                )
                accepted += 1
        
        except Exception as exc:
            logger.error(f"Error processing file {idx + 1}: {exc}")
            errors.append(f"File {idx + 1}: {str(exc)}")
            rejected += 1
    
    return BatchUploadResponse(
        total_files=len(files),
        accepted=accepted,
        rejected=rejected,
        tasks=tasks,
        errors=errors,
    )
