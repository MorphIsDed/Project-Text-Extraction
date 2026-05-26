// ============================================================
// Constants — Document Type Field Mappings
// ============================================================

import type { DocumentType } from '@/api/types';

/** Field definition: [key, display label] */
export type FieldDef = [string, string];

/** Field sets for each document type */
export const FIELD_SETS: Record<string, FieldDef[]> = {
  aadhaar: [
    ['name', 'Name'],
    ['date_of_birth', 'Date of Birth'],
    ['gender', 'Gender'],
    ['aadhaar_number_masked', 'Aadhaar Number'],
    ['address', 'Address'],
    ['pin_code', 'PIN Code'],
    ['side_detected', 'Card Side'],
  ],
  pan: [
    ['name', 'Name'],
    ['father_name', 'Father Name'],
    ['date_of_birth', 'Date of Birth'],
    ['pan_number', 'PAN Number'],
  ],
  invoice: [
    ['vendor_name', 'Vendor Name'],
    ['vendor_gstin', 'Vendor GSTIN'],
    ['invoice_number', 'Invoice Number'],
    ['invoice_date', 'Invoice Date'],
    ['buyer_name', 'Buyer Name'],
    ['buyer_gstin', 'Buyer GSTIN'],
    ['subtotal', 'Subtotal'],
    ['gst_amount', 'GST Amount'],
    ['total_amount', 'Total Amount'],
    ['currency', 'Currency'],
  ],
  ekyc: [
    ['applicant_name', 'Applicant Name'],
    ['date_of_birth', 'Date of Birth'],
    ['gender', 'Gender'],
    ['address', 'Address'],
    ['mobile_number', 'Mobile Number'],
    ['email', 'Email'],
    ['account_type', 'Account Type'],
    ['bank_name', 'Bank Name'],
  ],
  voter_id: [
    ['name', 'Name'],
    ['date_of_birth', 'Date of Birth'],
    ['voter_id_number', 'Voter ID Number'],
    ['address', 'Address'],
  ],
  driving_licence: [
    ['name', 'Name'],
    ['date_of_birth', 'Date of Birth'],
    ['licence_number', 'Licence Number'],
    ['date_of_issue', 'Date of Issue'],
    ['date_of_expiry', 'Date of Expiry'],
    ['address', 'Address'],
    ['vehicle_classes', 'Vehicle Classes'],
    ['issuing_rto', 'Issuing RTO'],
  ],
  passport: [
    ['surname', 'Surname'],
    ['given_name', 'Given Name'],
    ['date_of_birth', 'Date of Birth'],
    ['gender', 'Gender'],
    ['passport_number', 'Passport Number'],
    ['date_of_issue', 'Date of Issue'],
    ['date_of_expiry', 'Date of Expiry'],
    ['place_of_birth', 'Place of Birth'],
    ['nationality', 'Nationality'],
  ],
};

/** Fallback fields for unknown document types */
export const FALLBACK_FIELDS: FieldDef[] = [
  ['name', 'Name'],
  ['date_of_birth', 'Date of Birth'],
  ['id_number', 'ID Number'],
  ['address', 'Address'],
  ['invoice_number', 'Invoice Number'],
  ['total_amount', 'Total Amount'],
];

/** Document type display metadata */
export interface DocTypeMeta {
  label: string;
  colorClass: string;
  icon: string;
  gradient: string;
}

export const DOC_TYPE_META: Record<DocumentType, DocTypeMeta> = {
  aadhaar: {
    label: 'Aadhaar',
    colorClass: 'doc-badge--aadhaar',
    icon: '🪪',
    gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
  },
  pan: {
    label: 'PAN',
    colorClass: 'doc-badge--pan',
    icon: '💳',
    gradient: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
  },
  voter_id: {
    label: 'Voter ID',
    colorClass: 'doc-badge--voter',
    icon: '🗳️',
    gradient: 'linear-gradient(135deg, #10b981, #3b82f6)',
  },
  driving_licence: {
    label: 'Driving Licence',
    colorClass: 'doc-badge--licence',
    icon: '🚗',
    gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
  },
  passport: {
    label: 'Passport',
    colorClass: 'doc-badge--passport',
    icon: '🛂',
    gradient: 'linear-gradient(135deg, #06b6d4, #8b5cf6)',
  },
  invoice: {
    label: 'Invoice',
    colorClass: 'doc-badge--invoice',
    icon: '📄',
    gradient: 'linear-gradient(135deg, #f59e0b, #ea580c)',
  },
  ekyc: {
    label: 'eKYC',
    colorClass: 'doc-badge--ekyc',
    icon: '🔐',
    gradient: 'linear-gradient(135deg, #10b981, #059669)',
  },
  unknown: {
    label: 'Unknown',
    colorClass: 'doc-badge--unknown',
    icon: '❓',
    gradient: 'linear-gradient(135deg, #64748b, #475569)',
  },
};

/** Get field set for a document type, with fallback */
export function getFieldSet(documentType: string): FieldDef[] {
  return FIELD_SETS[documentType.toLowerCase()] || FALLBACK_FIELDS;
}

/** Get document type metadata */
export function getDocTypeMeta(documentType: string): DocTypeMeta {
  const key = documentType.toLowerCase() as DocumentType;
  return DOC_TYPE_META[key] || DOC_TYPE_META.unknown;
}
