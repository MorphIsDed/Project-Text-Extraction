import { motion } from 'framer-motion';
import type { ReviewFlag } from '@/api/types';
import './FieldCard.css';

interface FieldCardProps {
  label: string;
  value: string | number | string[] | undefined;
  reviewFlags?: ReviewFlag[];
  fieldKey: string;
}

function renderValue(value: FieldCardProps['value']) {
  if (value === undefined || value === null || value === '') {
    return <span className="field-card__value field-card__value--empty">Not found</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="field-card__value field-card__value--empty">Not found</span>;
    }
    return (
      <div className="field-card__array">
        {value.map((item, i) => (
          <span key={i} className="field-card__array-tag">
            {item}
          </span>
        ))}
      </div>
    );
  }

  return <span className="field-card__value">{String(value)}</span>;
}

export function FieldCard({ label, value, reviewFlags = [], fieldKey }: FieldCardProps) {
  const fieldFlags = reviewFlags.filter((f) => f.field === fieldKey);
  const hasReview = fieldFlags.length > 0;

  return (
    <motion.div
      className={`field-card ${hasReview ? 'field-card--review' : ''}`}
      whileHover={{ scale: 1.02, boxShadow: '0 12px 40px rgba(0, 0, 0, 0.5)' }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      role="group"
      aria-label={`${label}: ${value ?? 'Not found'}`}
    >
      {hasReview && (
        <motion.span
          className="field-card__review-badge"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 25, delay: 0.2 }}
        >
          <span className="field-card__review-badge-dot" aria-hidden="true" />
          Review
        </motion.span>
      )}

      <span className="field-card__label">{label}</span>
      {renderValue(value)}

      {fieldFlags.map((flag, i) => (
        <span key={i} className="field-card__review-note">
          {flag.reason}
        </span>
      ))}
    </motion.div>
  );
}
