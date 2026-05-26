import { useState, useCallback, useRef, useEffect } from 'react';
import { uploadDocument, getTaskStatus, getTaskResult } from '@/api/client';
import type {
  ExtractedDocument,
} from '@/api/types';
import { isDocumentResponse, isTaskCreateResponse } from '@/api/types';

export interface UploadState {
  /** Current processing step (0=idle, 1=uploading, 2=classifying, 3=extracting, 4=complete) */
  step: number;
  /** Overall status */
  status: 'idle' | 'processing' | 'completed' | 'failed';
  /** Progress percentage (0-100) */
  progress: number;
  /** Status message for display */
  message: string;
  /** Error message if failed */
  error?: string;
  /** Extracted document data when complete */
  result?: {
    extracted_data: ExtractedDocument;
    download_url?: string;
    filename?: string;
    raw_response: Record<string, unknown>;
  };
}

const INITIAL_STATE: UploadState = {
  step: 0,
  status: 'idle',
  progress: 0,
  message: '',
};

/** Polling constants */
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30;

/**
 * Map a backend progress value (0-100) to a processing step.
 *  0-30%  → step 2 (classifying)
 * 30-80%  → step 3 (extracting)
 * 80-100% → step 4 (complete)
 */
function progressToStep(progress: number): number {
  if (progress >= 80) return 4;
  if (progress >= 30) return 3;
  return 2;
}

export function useUpload() {
  const [state, setState] = useState<UploadState>(INITIAL_STATE);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // Clean up polling on unmount
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
  }, []);

  const startPolling = useCallback(
    (taskId: string) => {
      let attempts = 0;

      pollingRef.current = setInterval(async () => {
        if (!mountedRef.current) {
          stopPolling();
          return;
        }

        attempts += 1;

        if (attempts > MAX_POLL_ATTEMPTS) {
          stopPolling();
          setState((prev) => ({
            ...prev,
            status: 'failed',
            error: 'Processing timed out. Please try again.',
            message: 'Timed out',
          }));
          return;
        }

        try {
          const taskStatus = await getTaskStatus(taskId);

          if (!mountedRef.current) return;

          if (taskStatus.status === 'completed') {
            stopPolling();

            // Fetch full result
            try {
              const taskResult = await getTaskResult(taskId);
              if (!mountedRef.current) return;

              if (taskResult.extracted_data) {
                setState({
                  step: 4,
                  status: 'completed',
                  progress: 100,
                  message: 'Processing complete',
                  result: {
                    extracted_data: taskResult.extracted_data,
                    download_url: taskResult.download_url,
                    filename: taskResult.filename,
                    raw_response: taskResult as unknown as Record<string, unknown>,
                  },
                });
              } else {
                setState({
                  step: 4,
                  status: 'failed',
                  progress: 100,
                  message: 'No data extracted',
                  error: taskResult.error_message || 'No extracted data returned from server.',
                });
              }
            } catch (resultErr) {
              if (!mountedRef.current) return;
              setState((prev) => ({
                ...prev,
                status: 'failed',
                error:
                  resultErr instanceof Error
                    ? resultErr.message
                    : 'Failed to fetch results.',
                message: 'Error fetching results',
              }));
            }
            return;
          }

          if (taskStatus.status === 'failed') {
            stopPolling();
            setState((prev) => ({
              ...prev,
              status: 'failed',
              error: taskStatus.error_message || 'Processing failed on the server.',
              message: 'Processing failed',
            }));
            return;
          }

          // Still processing – update progress
          const backendProgress = taskStatus.progress ?? 0;
          setState((prev) => ({
            ...prev,
            step: progressToStep(backendProgress),
            progress: Math.max(prev.progress, backendProgress),
            message:
              backendProgress < 30
                ? 'Classifying document…'
                : backendProgress < 80
                  ? 'Extracting data…'
                  : 'Finalizing…',
          }));
        } catch (err) {
          // Network errors during polling are non-fatal; we'll retry
          console.warn('[useUpload] poll error, retrying…', err);
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  const upload = useCallback(
    async (file: File) => {
      // Reset from any prior state
      stopPolling();

      setState({
        step: 1,
        status: 'processing',
        progress: 10,
        message: 'Uploading document…',
      });

      try {
        const response = await uploadDocument(file);

        if (!mountedRef.current) return;

        // Immediate / cached result
        if (isDocumentResponse(response)) {
          setState({
            step: 4,
            status: 'completed',
            progress: 100,
            message: 'Processing complete (cached)',
            result: {
              extracted_data: response.extracted_data,
              download_url: response.download_url,
              filename: response.filename,
              raw_response: response as unknown as Record<string, unknown>,
            },
          });
          return;
        }

        // Async task created – start polling
        if (isTaskCreateResponse(response)) {
          setState((prev) => ({
            ...prev,
            step: 2,
            progress: 15,
            message: 'Classifying document…',
          }));
          startPolling(response.task_id);
          return;
        }
      } catch (err) {
        if (!mountedRef.current) return;
        setState({
          step: 1,
          status: 'failed',
          progress: 0,
          message: 'Upload failed',
          error: err instanceof Error ? err.message : 'Unknown upload error.',
        });
      }
    },
    [startPolling, stopPolling],
  );

  const reset = useCallback(() => {
    stopPolling();
    setState(INITIAL_STATE);
  }, [stopPolling]);

  return { state, upload, reset };
}
