// ============================================================
// TypeScript Types — Mirrored from Backend Pydantic Schemas
// ============================================================

// Enums
export type DocumentType =
  | 'aadhaar'
  | 'pan'
  | 'voter_id'
  | 'driving_licence'
  | 'passport'
  | 'invoice'
  | 'ekyc'
  | 'unknown';

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type ReviewSeverity = 'low' | 'medium' | 'high';

export type ProcessingStatus = 'success' | 'partial' | 'failed' | 'needs_review';

// Review Flag
export interface ReviewFlag {
  field: string;
  severity: ReviewSeverity;
  reason: string;
}

// Base Document fields
export interface BaseDocumentFields {
  document_id: string;
  document_type: DocumentType;
  processing_status: ProcessingStatus;
  review_flags: ReviewFlag[];
  review_notes: string[];
  needs_review: boolean;
}

// Document-specific types
export interface AadhaarDocument extends BaseDocumentFields {
  document_type: 'aadhaar';
  name?: string;
  date_of_birth?: string;
  gender?: string;
  father_name?: string;
  aadhaar_number_masked?: string;
  address?: string;
  pin_code?: string;
  side_detected?: string;
}

export interface PANDocument extends BaseDocumentFields {
  document_type: 'pan';
  name?: string;
  father_name?: string;
  date_of_birth?: string;
  pan_number?: string;
}

export interface VoterIDDocument extends BaseDocumentFields {
  document_type: 'voter_id';
  name?: string;
  father_name?: string;
  date_of_birth?: string;
  gender?: string;
  voter_id_number?: string;
  address?: string;
  polling_station?: string;
  assembly_constituency?: string;
  side_detected?: string;
}

export interface DrivingLicenseDocument extends BaseDocumentFields {
  document_type: 'driving_licence';
  name?: string;
  date_of_birth?: string;
  licence_number?: string;
  date_of_issue?: string;
  date_of_expiry?: string;
  address?: string;
  vehicle_classes?: string[];
  issuing_rto?: string;
}

export interface PassportDocument extends BaseDocumentFields {
  document_type: 'passport';
  surname?: string;
  given_name?: string;
  date_of_birth?: string;
  gender?: string;
  passport_number?: string;
  date_of_issue?: string;
  date_of_expiry?: string;
  place_of_birth?: string;
  nationality?: string;
  mrz_line1?: string;
  mrz_line2?: string;
}

export interface InvoiceLineItem {
  item_name?: string;
  description?: string;
  quantity?: number;
  unit_price?: number;
  total_price?: number;
}

export interface InvoiceDocument extends BaseDocumentFields {
  document_type: 'invoice';
  vendor_name?: string;
  vendor_gstin?: string;
  buyer_name?: string;
  buyer_gstin?: string;
  invoice_number?: string;
  invoice_date?: string;
  subtotal?: number;
  gst_amount?: number;
  total_amount?: number;
  currency?: string;
  line_items?: InvoiceLineItem[];
}

export interface EKYCDocument extends BaseDocumentFields {
  document_type: 'ekyc';
  applicant_name?: string;
  date_of_birth?: string;
  gender?: string;
  mobile_number?: string;
  email?: string;
  address?: string;
  account_type?: string;
  bank_name?: string;
}

export interface UnknownDocument extends BaseDocumentFields {
  document_type: 'unknown';
  detected_document_type?: string;
  summary?: string;
  raw_text?: string;
}

// Union type
export type ExtractedDocument =
  | AadhaarDocument
  | PANDocument
  | VoterIDDocument
  | DrivingLicenseDocument
  | PassportDocument
  | InvoiceDocument
  | EKYCDocument
  | UnknownDocument;

// API Response Types

/** Response when upload results in immediate (cached) result */
export interface DocumentResponse {
  success: boolean;
  filename: string;
  extracted_data: ExtractedDocument;
  message?: string;
  json_output_file?: string;
  download_url?: string;
  file_hash?: string;
}

/** Response when upload creates a new async task */
export interface TaskCreateResponse {
  task_id: string;
  status: TaskStatus;
  message: string;
  cached: boolean;
}

/** Upload can return either a cached result or a new task */
export type UploadResponse = DocumentResponse | TaskCreateResponse;

/** Task status polling response */
export interface TaskStatusResponse {
  task_id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  estimated_time_remaining?: number;
}

/** Task result response */
export interface TaskResultResponse {
  task_id: string;
  filename: string;
  status: TaskStatus;
  extracted_data?: ExtractedDocument;
  json_output_file?: string;
  download_url?: string;
  error_message?: string;
}

/** Batch upload response */
export interface BatchUploadResponse {
  total_files: number;
  accepted: number;
  rejected: number;
  tasks: TaskCreateResponse[];
  errors: string[];
}

/** Task list item */
export interface TaskListItem {
  task_id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  created_at: string;
  completed_at?: string;
}

/** Task list response */
export interface TaskListResponse {
  total: number;
  tasks: TaskListItem[];
}

// Type Guards

export function isDocumentResponse(response: UploadResponse): response is DocumentResponse {
  return 'success' in response && 'extracted_data' in response;
}

export function isTaskCreateResponse(response: UploadResponse): response is TaskCreateResponse {
  return 'task_id' in response && !('extracted_data' in response);
}
