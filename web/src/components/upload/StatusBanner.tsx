// ============================================================
// StatusBanner — Animated Alert Banner
// ============================================================

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import './StatusBanner.css';

interface StatusBannerProps {
  type: 'success' | 'error' | 'info';
  message: string;
  onDismiss?: () => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  type,
  message,
  onDismiss,
}) => {
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="status-banner__icon" aria-hidden="true" />;
      case 'error':
        return <AlertCircle className="status-banner__icon" aria-hidden="true" />;
      case 'info':
      default:
        return <Info className="status-banner__icon" aria-hidden="true" />;
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -15, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -15, scale: 0.95 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={`status-banner status-banner--${type}`}
      role="alert"
    >
      {getIcon()}
      <div className="status-banner__content">{message}</div>
      {onDismiss && (
        <button
          type="button"
          className="status-banner__close"
          onClick={onDismiss}
          aria-label="Dismiss message"
        >
          <X size={16} />
        </button>
      )}
    </motion.div>
  );
};
