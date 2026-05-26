// ============================================================
// Constants — File Upload Configuration
// ============================================================

export const ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/bmp',
  'image/tiff',
  'image/webp',
]);

export const ALLOWED_EXTENSIONS = /\.(pdf|jpe?g|png|bmp|tiff?|webp)$/i;

export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

export const MAX_BATCH_SIZE = 20;

export const FILE_TYPE_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'image/jpeg': 'JPEG',
  'image/png': 'PNG',
  'image/bmp': 'BMP',
  'image/tiff': 'TIFF',
  'image/webp': 'WebP',
};

export const ACCEPTED_FILE_STRING = '.pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp';
