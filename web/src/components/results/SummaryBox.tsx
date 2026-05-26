import { motion } from 'framer-motion';
import type { ExtractedDocument } from '@/api/types';
import { DocumentBadge } from '@/components/results/DocumentBadge';
import './SummaryBox.css';

interface SummaryBoxProps {
  data: ExtractedDocument;
}

const STATUS_LABELS: Record<string, string> = {
  success: 'Success',
  partial: 'Partial',
  failed: 'Failed',
  needs_review: 'Needs Review',
};

function buildSummary(data: ExtractedDocument): string {
  const type = data.document_type;

  // Try to find a name-like field for a quick summary sentence
  const record = data as unknown as Record<string, unknown>;
  const name =
    (record.name as string) ??
    (record.applicant_name as string) ??
    (record.vendor_name as string) ??
    (record.surname as string);

  if (type === 'unknown') {
    return (
      (record.summary as string) ??
      'This document could not be classified into a known type.'
    );
  }

  const parts: string[] = [];
  if (name) parts.push(`Identified as ${name}.`);

  const fieldCount = Object.keys(record).filter(
    (k) =>
      ![
        'document_id',
        'document_type',
        'processing_status',
        'review_flags',
        'review_notes',
        'needs_review',
      ].includes(k) && record[k] !== undefined && record[k] !== null
  ).length;

  parts.push(`${fieldCount} field${fieldCount !== 1 ? 's' : ''} extracted from ${type.replace(/_/g, ' ')} document.`);

  if (data.needs_review) {
    parts.push('Manual review recommended.');
  }

  return parts.join(' ');
}

export function SummaryBox({ data }: SummaryBoxProps) {
  const summary = buildSummary(data);
  const statusClass = `summary-box__status--${data.processing_status}`;
  const statusLabel = STATUS_LABELS[data.processing_status] ?? data.processing_status;

  return (
    <motion.div
      className={`summary-box ${data.needs_review ? 'summary-box--review' : ''}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] as const }}
      role="region"
      aria-label="Document summary"
    >
      <div className="summary-box__badge-row">
        <DocumentBadge documentType={data.document_type} />

        <motion.span
          className={`summary-box__status ${statusClass}`}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
          role="status"
          aria-label={`Processing status: ${statusLabel}`}
        >
          <span className="summary-box__status-dot" aria-hidden="true" />
          {statusLabel}
        </motion.span>
      </div>

      <div>
        <span className="summary-box__heading">Summary</span>
        <motion.p
          className="summary-box__text"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          {summary}
        </motion.p>
      </div>

      <div className="summary-box__doc-id">
        <span className="summary-box__doc-id-label">Doc ID</span>
        <span className="summary-box__doc-id-value">{data.document_id}</span>
      </div>
    </motion.div>
  );
}
