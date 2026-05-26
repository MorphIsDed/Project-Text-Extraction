import { motion } from 'framer-motion';
import { getDocTypeMeta } from '@/constants/documentTypes';
import './DocumentBadge.css';

interface DocumentBadgeProps {
  documentType: string;
}

export function DocumentBadge({ documentType }: DocumentBadgeProps) {
  const meta = getDocTypeMeta(documentType);

  return (
    <motion.span
      className={`doc-badge ${meta.colorClass}`}
      style={{ background: meta.gradient }}
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 20,
      }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.97 }}
      role="status"
      aria-label={`Document type: ${meta.label}`}
    >
      <span className="doc-badge__icon" aria-hidden="true">
        {meta.icon}
      </span>
      <span className="doc-badge__label">{meta.label}</span>
    </motion.span>
  );
}
