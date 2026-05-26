// ============================================================
// UploadButton — Animated Submit Button
// ============================================================

import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import './UploadButton.css';

interface UploadButtonProps {
  state: 'disabled' | 'ready' | 'loading';
  onClick: () => void;
  label?: string;
}

export const UploadButton: React.FC<UploadButtonProps> = ({
  state,
  onClick,
  label,
}) => {
  const isDisabled = state === 'disabled';
  const isLoading = state === 'loading';

  // Determine button text
  const getButtonText = () => {
    if (label) return label;
    if (isLoading) return 'Processing...';
    if (isDisabled) return 'Select a File';
    return 'Process Document';
  };

  return (
    <motion.button
      type="button"
      className={`upload-button ${isDisabled ? 'upload-button--disabled' : ''} ${isLoading ? 'upload-button--loading' : ''}`}
      onClick={onClick}
      disabled={isDisabled || isLoading}
      whileHover={!isDisabled && !isLoading ? { scale: 1.01 } : {}}
      whileTap={!isDisabled && !isLoading ? { scale: 0.99 } : {}}
      aria-busy={isLoading}
      aria-disabled={isDisabled}
    >
      <span className="upload-button__content">
        {isLoading && <Loader2 className="upload-button__spinner" aria-hidden="true" />}
        <span>{getButtonText()}</span>
      </span>
      {!isDisabled && !isLoading && <div className="upload-button__shine" />}
    </motion.button>
  );
};
