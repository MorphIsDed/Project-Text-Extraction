// ============================================================
// Utility Functions — File Validators
// ============================================================

import { ALLOWED_MIME_TYPES, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES } from '@/constants/fileConfig';
import { formatBytes } from './formatters';

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/** Validate a single file for upload */
export function validateFile(file: File): ValidationResult {
  // Check file type
  if (!ALLOWED_EXTENSIONS.test(file.name) && !ALLOWED_MIME_TYPES.has(file.type)) {
    return {
      valid: false,
      error: 'Unsupported file type. Please upload a PDF or image (JPG, PNG, BMP, TIFF, WEBP).',
    };
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: `File is too large (${formatBytes(file.size)}). Maximum allowed size is 10 MB.`,
    };
  }

  return { valid: true };
}

/** Validate multiple files for batch upload */
export function validateFiles(files: File[]): {
  validFiles: File[];
  errors: string[];
} {
  const validFiles: File[] = [];
  const errors: string[] = [];

  for (const file of files) {
    const result = validateFile(file);
    if (result.valid) {
      validFiles.push(file);
    } else {
      errors.push(`${file.name}: ${result.error}`);
    }
  }

  return { validFiles, errors };
}

/** Get file extension icon type */
export function getFileIconType(filename: string): 'pdf' | 'image' {
  return filename.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image';
}
