// ============================================================
// Component — FilePreview (Selected File Preview Card)
// ============================================================

import { motion } from 'framer-motion';
import { FileText, Image, X } from 'lucide-react';
import { formatBytes } from '@/utils/formatters';
import { getFileIconType } from '@/utils/validators';
import './FilePreview.css';

interface FilePreviewProps {
  file: File;
  onRemove: () => void;
}

export function FilePreview({ file, onRemove }: FilePreviewProps) {
  const iconType = getFileIconType(file.name);
  const IconComponent = iconType === 'pdf' ? FileText : Image;

  return (
    <motion.div
      className="file-preview"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 25,
      }}
      layout
    >
      {/* File type icon */}
      <motion.div
        className={`file-preview__icon file-preview__icon--${iconType}`}
        initial={{ rotate: -10 }}
        animate={{ rotate: 0 }}
        transition={{ type: 'spring', stiffness: 300 }}
      >
        <IconComponent />
      </motion.div>

      {/* File info */}
      <div className="file-preview__info">
        <p className="file-preview__name" title={file.name}>
          {file.name}
        </p>
        <p className="file-preview__size">{formatBytes(file.size)}</p>
      </div>

      {/* Remove button */}
      <motion.button
        className="file-preview__remove"
        onClick={onRemove}
        aria-label={`Remove file ${file.name}`}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.9 }}
        type="button"
      >
        <X />
      </motion.button>
    </motion.div>
  );
}
