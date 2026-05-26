import { useState, useCallback, useRef, useEffect } from 'react';
import { batchUploadDocuments, getTaskStatus, getTaskResult } from '@/api/client';
import type { ExtractedDocument } from '@/api/types';

export interface BatchFileState {
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  taskId?: string;
  error?: string;
  result?: {
    extracted_data: ExtractedDocument;
    download_url?: string;
  };
}

export interface BatchUploadState {
  files: BatchFileState[];
  overallProgress: number;
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'failed';
}

const INITIAL_STATE: BatchUploadState = {
  files: [],
  overallProgress: 0,
  status: 'idle',
};

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 30;

/**
 * Compute overall progress as a simple average across all files.
 */
function computeOverallProgress(files: BatchFileState[]): number {
  if (files.length === 0) return 0;
  const total = files.reduce((sum, f) => sum + f.progress, 0);
  return Math.round(total / files.length);
}

/**
 * Derive overall status from individual file statuses.
 */
function computeOverallStatus(files: BatchFileState[]): BatchUploadState['status'] {
  if (files.length === 0) return 'idle';
  const statuses = files.map((f) => f.status);
  if (statuses.every((s) => s === 'pending')) return 'idle';
  if (statuses.every((s) => s === 'completed')) return 'completed';
  if (statuses.some((s) => s === 'failed') && statuses.every((s) => s === 'completed' || s === 'failed')) return 'failed';
  if (statuses.some((s) => s === 'uploading')) return 'uploading';
  return 'processing';
}

export function useBatchUpload() {
  const [state, setState] = useState<BatchUploadState>(INITIAL_STATE);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const pollAttemptsRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    pollAttemptsRef.current = 0;
  }, []);

  /** Add files to the batch queue */
  const addFiles = useCallback((files: File[]) => {
    setState((prev) => {
      const newFiles: BatchFileState[] = files.map((file) => ({
        file,
        status: 'pending' as const,
        progress: 0,
      }));
      const merged = [...prev.files, ...newFiles];
      return {
        files: merged,
        overallProgress: computeOverallProgress(merged),
        status: computeOverallStatus(merged),
      };
    });
  }, []);

  /** Remove a file by index */
  const removeFile = useCallback((index: number) => {
    setState((prev) => {
      const updated = prev.files.filter((_, i) => i !== index);
      return {
        files: updated,
        overallProgress: computeOverallProgress(updated),
        status: computeOverallStatus(updated),
      };
    });
  }, []);

  /** Poll all in-flight tasks */
  const startPolling = useCallback(() => {
    pollAttemptsRef.current = 0;

    pollingRef.current = setInterval(async () => {
      if (!mountedRef.current) {
        stopPolling();
        return;
      }

      pollAttemptsRef.current += 1;

      if (pollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
        stopPolling();
        setState((prev) => {
          const updated = prev.files.map((f) =>
            f.status === 'processing' || f.status === 'uploading'
              ? { ...f, status: 'failed' as const, error: 'Timed out' }
              : f,
          );
          return {
            files: updated,
            overallProgress: computeOverallProgress(updated),
            status: computeOverallStatus(updated),
          };
        });
        return;
      }

      setState((prev) => {
        // Find tasks that still need polling
        const tasksToCheck = prev.files.filter(
          (f) => f.taskId && (f.status === 'processing' || f.status === 'uploading'),
        );

        if (tasksToCheck.length === 0) {
          // All done – stop polling from outside this setState
          queueMicrotask(() => stopPolling());
          return prev;
        }

        // Fire off status checks (async, results handled via subsequent setState)
        for (const fileState of tasksToCheck) {
          pollSingleTask(fileState.taskId!);
        }

        return prev;
      });
    }, POLL_INTERVAL_MS);
  }, [stopPolling]);

  /** Poll a single task and update state accordingly */
  const pollSingleTask = useCallback(async (taskId: string) => {
    try {
      const taskStatus = await getTaskStatus(taskId);
      if (!mountedRef.current) return;

      if (taskStatus.status === 'completed') {
        // Fetch full result
        try {
          const taskResult = await getTaskResult(taskId);
          if (!mountedRef.current) return;

          setState((prev) => {
            const updated = prev.files.map((f) =>
              f.taskId === taskId
                ? {
                    ...f,
                    status: 'completed' as const,
                    progress: 100,
                    result: taskResult.extracted_data
                      ? {
                          extracted_data: taskResult.extracted_data,
                          download_url: taskResult.download_url,
                        }
                      : undefined,
                    error: taskResult.extracted_data
                      ? undefined
                      : taskResult.error_message || 'No data extracted',
                  }
                : f,
            );
            return {
              files: updated,
              overallProgress: computeOverallProgress(updated),
              status: computeOverallStatus(updated),
            };
          });
        } catch (err) {
          if (!mountedRef.current) return;
          setState((prev) => {
            const updated = prev.files.map((f) =>
              f.taskId === taskId
                ? {
                    ...f,
                    status: 'failed' as const,
                    error: err instanceof Error ? err.message : 'Failed to fetch result',
                  }
                : f,
            );
            return {
              files: updated,
              overallProgress: computeOverallProgress(updated),
              status: computeOverallStatus(updated),
            };
          });
        }
        return;
      }

      if (taskStatus.status === 'failed') {
        setState((prev) => {
          const updated = prev.files.map((f) =>
            f.taskId === taskId
              ? {
                  ...f,
                  status: 'failed' as const,
                  progress: f.progress,
                  error: taskStatus.error_message || 'Processing failed',
                }
              : f,
          );
          return {
            files: updated,
            overallProgress: computeOverallProgress(updated),
            status: computeOverallStatus(updated),
          };
        });
        return;
      }

      // Still processing – update progress
      const backendProgress = taskStatus.progress ?? 0;
      setState((prev) => {
        const updated = prev.files.map((f) =>
          f.taskId === taskId
            ? {
                ...f,
                progress: Math.max(f.progress, backendProgress),
              }
            : f,
        );
        return {
          files: updated,
          overallProgress: computeOverallProgress(updated),
          status: computeOverallStatus(updated),
        };
      });
    } catch {
      // Network errors during polling are non-fatal; retry on next tick
      console.warn(`[useBatchUpload] poll error for task ${taskId}, will retry`);
    }
  }, []);

  /** Upload all pending files */
  const uploadAll = useCallback(async () => {
    stopPolling();

    // Mark all pending files as uploading
    setState((prev) => {
      const updated = prev.files.map((f) =>
        f.status === 'pending' ? { ...f, status: 'uploading' as const, progress: 5 } : f,
      );
      return {
        files: updated,
        overallProgress: computeOverallProgress(updated),
        status: 'uploading',
      };
    });

    try {
      // Gather pending files for the batch call
      const pendingFiles = state.files
        .filter((f) => f.status === 'pending' || f.status === 'uploading')
        .map((f) => f.file);

      if (pendingFiles.length === 0) return;

      const response = await batchUploadDocuments(pendingFiles);
      if (!mountedRef.current) return;

      // Map task IDs back to files
      setState((prev) => {
        let taskIndex = 0;
        const updated = prev.files.map((f) => {
          if (f.status === 'uploading' && taskIndex < response.tasks.length) {
            const task = response.tasks[taskIndex]!;
            taskIndex += 1;
            return {
              ...f,
              status: 'processing' as const,
              progress: 15,
              taskId: task.task_id,
            };
          }
          return f;
        });

        // Mark any overflow as failed (rejected by server)
        const errorMessages = response.errors || [];
        if (errorMessages.length > 0) {
          let errIdx = 0;
          for (let i = 0; i < updated.length; i++) {
            const currentItem = updated[i];
            if (currentItem && currentItem.status === 'uploading' && errIdx < errorMessages.length) {
              updated[i] = {
                ...currentItem,
                status: 'failed' as const,
                error: errorMessages[errIdx],
              };
              errIdx += 1;
            }
          }
        }

        return {
          files: updated,
          overallProgress: computeOverallProgress(updated),
          status: computeOverallStatus(updated),
        };
      });

      // Start polling for task updates
      startPolling();
    } catch (err) {
      if (!mountedRef.current) return;
      setState((prev) => {
        const updated = prev.files.map((f) =>
          f.status === 'uploading'
            ? {
                ...f,
                status: 'failed' as const,
                error: err instanceof Error ? err.message : 'Batch upload failed',
              }
            : f,
        );
        return {
          files: updated,
          overallProgress: computeOverallProgress(updated),
          status: 'failed',
        };
      });
    }
  }, [state.files, startPolling, stopPolling]);

  /** Reset everything */
  const reset = useCallback(() => {
    stopPolling();
    setState(INITIAL_STATE);
  }, [stopPolling]);

  return { state, addFiles, removeFile, uploadAll, reset };
}
