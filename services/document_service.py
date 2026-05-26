"""
Document service main orchestrator.

Pipeline:
1. Run OCR for lightweight classification.
2. Extract fields with the configured LLM path (returns typed document).
3. Post-process typed document.
4. Serialize to API response format.

NEW ARCHITECTURE:
- Works with typed documents (ExtractedDocument)
- Separates document data from metadata
- Uses serializer for API responses
"""

import logging
import time
import uuid
from typing import Optional

from services.document_classifier import classify_document
from services.llm_service import extract_document
from services.post_processing import post_process_document
from models.schemas import serialize_document_response, DocumentResponse, document_to_json

logger = logging.getLogger(__name__)


async def process_document(
    file_path: str,
    task_id: Optional[str] = None,
    return_format: str = "dict"
) -> dict:
    """
    Main document processing pipeline.
    
    NEW ARCHITECTURE:
    - Extracts typed document (not dict)
    - Post-processes typed document
    - Returns dict for backward compatibility (default)
    - Can return DocumentResponse for new API
    
    Args:
        file_path: Path to uploaded image or PDF
        task_id: Optional task ID for logging
        return_format: "dict" (legacy) or "response" (new typed API)
    
    Returns:
        Complete extraction result with metadata (dict format for backward compatibility)
    """
    start_time = time.time()
    file_path = str(file_path)
    
    # Generate request_id if not provided via task_id
    request_id = task_id or str(uuid.uuid4())
    
    logger.info(f"[{request_id}] Processing: {file_path}")
    
    # Step 1: OCR + Classification
    try:
        from services.ocr_service import extract_text
        
        ocr_text, ocr_confidence = extract_text(file_path)
        doc_type, class_confidence = classify_document(ocr_text)
    except Exception as e:
        logger.warning(f"[{request_id}] OCR/Classification failed: {e}")
        ocr_text = ""
        ocr_confidence = 0.0
        doc_type = "unknown"
        class_confidence = 0.0
    
    logger.info(f"[{request_id}] Classified as: {doc_type} ({class_confidence:.2f})")
    
    # Step 2: Extract (returns typed document + metadata)
    document, extraction_metadata = extract_document(file_path, doc_type)
    
    # Step 3: Post-process (returns typed document)
    document = post_process_document(
        document,
        ocr_text=ocr_text,
        request_id=request_id
    )
    
    # Calculate total time
    total_time_ms = round((time.time() - start_time) * 1000, 2)
    
    logger.info(
        f"[{request_id}] Done in {total_time_ms}ms | "
        f"Provider: {extraction_metadata.get('provider', 'unknown')} | "
        f"Status: {document.processing_status.value}"
    )
    
    # Return format based on caller needs
    if return_format == "response":
        # NEW: Return typed DocumentResponse
        response = serialize_document_response(
            document=document,
            filename=file_path.split("/")[-1],  # Extract filename
            request_id=request_id,
            processing_time_ms=total_time_ms,
            model_used=extraction_metadata.get("model_used"),
            fallback_used=extraction_metadata.get("fallback_used", False),
            ocr_used=extraction_metadata.get("ocr_used", False)
        )
        return response.model_dump()
    
    else:
        # LEGACY: Return dict format for backward compatibility
        # Convert typed document to dict
        document_dict = document_to_json(
            document,
            include_raw_fields=False,
            include_null_fields=True
        )
        
        # Add legacy metadata structure
        result = {
            **document_dict,
            "task_id": task_id,
            "file_path": file_path,
            "classification": {
                "document_type": doc_type,
                "confidence": class_confidence,
            },
            "processing_summary": {
                "total_time_seconds": round(total_time_ms / 1000, 2),
                "provider": extraction_metadata.get("provider", "unknown"),
                "ocr_used": extraction_metadata.get("ocr_used", False),
                "ocr_confidence": ocr_confidence,
            },
            "_metadata": {
                "request_id": request_id,
                "provider": extraction_metadata.get("provider"),
                "model_used": extraction_metadata.get("model_used"),
                "processing_time_ms": total_time_ms,
                "fallback_used": extraction_metadata.get("fallback_used", False),
                "ocr_used": extraction_metadata.get("ocr_used", False),
                "post_processed": True,
            }
        }
        
        return result
