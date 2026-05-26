"""
Task-related Pydantic models for async document processing.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from models.schemas import ExtractedDocument


class TaskStatus(str, Enum):
    """Task processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """Task metadata and status information."""
    task_id: str
    filename: str
    file_hash: str
    status: TaskStatus
    progress: float = Field(ge=0.0, le=100.0, default=0.0)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None  # seconds


class TaskCreateResponse(BaseModel):
    """Response when a task is created."""
    task_id: str
    status: TaskStatus
    message: str
    cached: bool = False  # True if result was cached


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""
    task_id: str
    filename: str
    status: TaskStatus
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None


class TaskResultResponse(BaseModel):
    """Response containing the completed task result."""
    task_id: str
    filename: str
    status: TaskStatus
    extracted_data: Optional[ExtractedDocument] = None
    json_output_file: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for batch upload requests."""
    total_files: int
    accepted: int
    rejected: int
    tasks: List[TaskCreateResponse]
    errors: List[str] = []


class BatchStatusRequest(BaseModel):
    """Request to check status of multiple tasks."""
    task_ids: List[str]


class BatchStatusResponse(BaseModel):
    """Response containing status of multiple tasks."""
    tasks: List[TaskStatusResponse]
