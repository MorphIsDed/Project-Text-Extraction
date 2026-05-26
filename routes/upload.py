import logging
import os
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import Union

from models.schemas import DocumentResponse, ExtractedDocument
from models.task_schemas import TaskCreateResponse, TaskStatus
from services.cache_manager import get_cache_manager
from services.task_queue import get_task_queue

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")


@router.post("/upload", response_model=Union[DocumentResponse, TaskCreateResponse])
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for processing.
    
    HYBRID RESPONSE BEHAVIOR:
    - If document hash exists in cache → Returns DocumentResponse immediately (<500ms)
    - If new document → Returns TaskCreateResponse with task_id (async processing)
    
    The frontend should check the response type:
    - DocumentResponse: Result is ready immediately
    - TaskCreateResponse: Poll /api/tasks/status/{task_id} for progress
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload PDF or image files."
        )

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # Compute file hash for deduplication
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(file_content)
    file_hash = hasher.hexdigest()[:12]
    
    # Check cache first
    cache_manager = get_cache_manager()
    cached_result = cache_manager.get(file_hash)
    
    if cached_result:
        if cached_result.get("error"):
            logger.info(f"Cached error result found for {filename}. Invalidating cache and reprocessing.")
            cache_manager.delete(file_hash)
            cached_result = None

    if cached_result:
        # Cache HIT - convert dict to DocumentResponse
        try:
            # Extract only the fields that belong to ExtractedDocument
            extracted = ExtractedDocument(**{
                k: v for k, v in cached_result.items()
                if k not in (
                    '_metadata',
                    'task_id',
                    'file_path',
                    'classification',
                    'processing_summary',
                    'json_output_file',
                    'download_url',
                )
            })
            return DocumentResponse(
                success=True,
                filename=filename,
                extracted_data=extracted,
                message="Result retrieved from cache.",
                json_output_file=cached_result.get("json_output_file"),
                download_url=cached_result.get("download_url"),
                file_hash=file_hash,
            )
        except Exception as e:
            logger.warning(f"Cache format mismatch, reprocessing: {e}")
            # Cache format is old, continue to reprocess below
    
    # Cache MISS - create task for async processing
    # Save file temporarily
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{file_hash}_{filename}")
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create task
    task_queue = get_task_queue()
    task_id = await task_queue.create_task(filename, file_hash)
    
    return TaskCreateResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Document queued for processing. Use task_id to check status.",
        cached=False,
    )


@router.get("/download/{json_filename}")
def download_json(json_filename: str):
    """Download processed document JSON output."""
    file_path = os.path.join(OUTPUT_DIR, json_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="JSON file not found.")
    return FileResponse(file_path, media_type="application/json", filename=json_filename)
