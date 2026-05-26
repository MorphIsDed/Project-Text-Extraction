import { motion } from 'framer-motion';
import type { ExtractedDocument } from '@/api/types';
import { getFieldSet } from '@/constants/documentTypes';
import { FieldCard } from '@/components/results/FieldCard';
import './FieldsGrid.css';

interface FieldsGridProps {
  data: ExtractedDocument;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.35,
      ease: [0.4, 0, 0.2, 1] as const,
    },
  },
};

export function FieldsGrid({ data }: FieldsGridProps) {
  const fields = getFieldSet(data.document_type);
  const record = data as unknown as Record<string, unknown>;

  return (
    <motion.div
      className="fields-grid"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      role="list"
      aria-label="Extracted fields"
    >
      {fields.map(([key, label]) => (
        <motion.div key={key} variants={itemVariants} role="listitem">
          <FieldCard
            label={label}
            value={record[key] as string | number | string[] | undefined}
            reviewFlags={data.review_flags}
            fieldKey={key}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
