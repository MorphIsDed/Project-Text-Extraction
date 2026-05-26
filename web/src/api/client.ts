// ============================================================
// API Client — Fetch wrapper for Document Intelligence API
// ============================================================

import type {
  UploadResponse,
  TaskStatusResponse,
  TaskResultResponse,
  BatchUploadResponse,
  TaskListResponse,
} from './types';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      // Response body was not JSON
    }
    throw new ApiError(
      response.status,
      detail || `Server error ${response.status}`,
      detail,
    );
  }
  return response.json() as Promise<T>;
}

/** Upload a single document */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

/** Get task status */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await fetch(`${API_BASE}/tasks/status/${taskId}`);
  return handleResponse<TaskStatusResponse>(response);
}

/** Get task result */
export async function getTaskResult(taskId: string): Promise<TaskResultResponse> {
  const response = await fetch(`${API_BASE}/tasks/result/${taskId}`);
  return handleResponse<TaskResultResponse>(response);
}

/** Batch upload multiple documents */
export async function batchUploadDocuments(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE}/batch-upload`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<BatchUploadResponse>(response);
}

/** List all tasks */
export async function listTasks(
  status?: string,
  limit: number = 100,
): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  params.set('limit', String(limit));

  const response = await fetch(`${API_BASE}/tasks/list?${params}`);
  return handleResponse<TaskListResponse>(response);
}

/** Get health status */
export async function getHealth(): Promise<Record<string, unknown>> {
  const response = await fetch('/health');
  return handleResponse<Record<string, unknown>>(response);
}

export { ApiError };
