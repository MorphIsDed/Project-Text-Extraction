// ============================================================
// Page — Batch Processing (Multi-file Upload)
// ============================================================

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Layers } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { DropZone } from '@/components/upload/DropZone';
import { UploadButton } from '@/components/upload/UploadButton';
import { useBatchUpload } from '@/api/hooks/useBatchUpload';
import { MAX_BATCH_SIZE } from '@/constants/fileConfig';
import { getDocTypeMeta } from '@/constants/documentTypes';
import './BatchPage.css';

const easeOutExpo = [0.16, 1, 0.3, 1] as const;

const pageTransition = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -24 },
  transition: { duration: 0.35, ease: easeOutExpo },
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const staggerItem = {
  hidden: { opacity: 0, y: 16, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.35, ease: easeOutExpo },
  },
  exit: {
    opacity: 0,
    scale: 0.92,
    transition: { duration: 0.2 },
  },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const BatchPage: React.FC = () => {
  const {
    state,
    addFiles,
    removeFile,
    uploadAll,
    reset,
  } = useBatchUpload();

  const { files, overallProgress, status } = state;

  const isProcessing = status === 'uploading' || status === 'processing';
  const completedCount = files.filter((f) => f.status === 'completed').length;
  const failedCount = files.filter((f) => f.status === 'failed').length;
  const isAtLimit = files.length >= MAX_BATCH_SIZE;

  const handleFileSelect = (file: File) => {
    if (files.length < MAX_BATCH_SIZE) {
      addFiles([file]);
    }
  };

  const clearFiles = () => {
    reset();
  };

  const processAll = () => {
    uploadAll();
  };

  // Extract results for display
  const completedResults = files
    .filter((f) => f.status === 'completed' && f.result?.extracted_data)
    .map((f) => ({
      data: f.result!.extracted_data,
      filename: f.file.name,
    }));

  return (
    <motion.div {...pageTransition}>
      <PageContainer
        title="Batch Processing"
        subtitle="Upload and process multiple documents at once"
      >
        <div className="batch-page">
          {/* ---- Upload Area ---- */}
          <motion.div
            className="batch-page__upload-area glass-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{ padding: '24px' }}
          >
            <DropZone
              onFileSelect={handleFileSelect}
              disabled={isProcessing || isAtLimit}
            />

            {/* File counter */}
            {files.length > 0 && (
              <div className="batch-page__file-counter" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', fontSize: '13px' }}>
                <span className="batch-page__file-count">
                  <strong>{files.length}</strong> file{files.length !== 1 ? 's' : ''} selected
                </span>
                <span
                  className={`batch-page__file-limit ${isAtLimit ? 'batch-page__file-limit--warning' : ''}`}
                >
                  Max {MAX_BATCH_SIZE} files
                </span>
              </div>
            )}

            {/* File Cards Grid */}
            <AnimatePresence mode="popLayout">
              {files.length > 0 ? (
                <motion.div
                  className="batch-page__file-grid"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                  key="file-grid"
                  style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginTop: '20px' }}
                >
                  {files.map((fileState, index) => {
                    const { file, status: fileStatus } = fileState;
                    return (
                      <motion.div
                        key={`${file.name}-${index}`}
                        className="batch-page__file-card glass-card"
                        variants={staggerItem}
                        exit="exit"
                        layout
                        whileHover={{ scale: 1.01 }}
                        style={{ padding: '16px', position: 'relative' }}
                      >
                        <div className="batch-page__file-card-header" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <span className="batch-page__file-card-name" title={file.name} style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {file.name}
                          </span>
                          <span className="batch-page__file-card-size" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {formatFileSize(file.size)}
                          </span>
                          {!isProcessing && (
                            <button
                              className="batch-page__file-card-remove"
                              onClick={() => removeFile(index)}
                              aria-label={`Remove ${file.name}`}
                              type="button"
                              style={{ position: 'absolute', top: '12px', right: '12px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                        <span className={`status-pill status-pill--${fileStatus}`} style={{ marginTop: '12px', display: 'inline-flex' }}>
                          {fileStatus === 'processing' && (
                            <motion.span
                              animate={{ rotate: 360 }}
                              transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                              style={{ display: 'inline-flex', marginRight: '4px' }}
                            >
                              ⟳
                            </motion.span>
                          )}
                          {fileStatus}
                        </span>
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  className="batch-page__empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', textAlign: 'center' }}
                >
                  <div className="batch-page__empty-icon" style={{ marginBottom: '12px', color: 'var(--text-muted)' }}>
                    <Layers size={28} />
                  </div>
                  <p className="batch-page__empty-text" style={{ color: 'var(--text-muted)' }}>
                    Add documents to process batch queue
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Actions */}
            {files.length > 0 && (
              <motion.div
                className="batch-page__actions"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                style={{ display: 'flex', gap: '12px', marginTop: '24px' }}
              >
                <div style={{ flex: 1 }}>
                  <UploadButton
                    state={isProcessing ? 'loading' : 'ready'}
                    onClick={processAll}
                    label="Process All"
                  />
                </div>
                {!isProcessing && (
                  <button
                    className="batch-page__clear-btn"
                    onClick={clearFiles}
                    type="button"
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', padding: '0 16px', borderRadius: 'var(--radius-md)', cursor: 'pointer', color: 'var(--text-primary)', transition: 'all 0.2s' }}
                  >
                    Clear All
                  </button>
                )}
              </motion.div>
            )}
          </motion.div>

          {/* ---- Progress Summary ---- */}
          <AnimatePresence>
            {isProcessing && (
              <motion.div
                className="batch-page__progress-section glass-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.4 }}
                style={{ padding: '20px', marginTop: '20px' }}
              >
                <div className="batch-page__progress-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span className="batch-page__progress-title" style={{ fontWeight: 600 }}>Overall Progress</span>
                  <span className="batch-page__progress-stats" style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    {completedCount + failedCount} / {files.length} complete
                  </span>
                </div>
                <div className="batch-page__progress-bar-track" role="progressbar" aria-valuenow={overallProgress} aria-valuemin={0} aria-valuemax={100} style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '9999px', overflow: 'hidden' }}>
                  <motion.div
                    className="batch-page__progress-bar-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${overallProgress}%` }}
                    transition={{ type: 'spring', stiffness: 80, damping: 20 }}
                    style={{ height: '100%', background: 'var(--accent-gradient)' }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ---- Results Grid ---- */}
          <AnimatePresence>
            {completedResults.length > 0 && (
              <motion.div
                className="batch-page__results-section"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                style={{ marginTop: '32px' }}
              >
                <span className="batch-page__results-title section-label" style={{ display: 'block', marginBottom: '16px' }}>Extracted Results</span>
                <motion.div
                  className="batch-page__results-grid"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                  style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}
                >
                  {completedResults.map((res, i) => {
                    const meta = getDocTypeMeta(res.data.document_type || 'unknown');
                    const fieldCount = Object.keys(res.data).filter(
                      (k) =>
                        !['document_id', 'document_type', 'processing_status', 'review_flags', 'review_notes', 'needs_review'].includes(k) &&
                        res.data[k as keyof typeof res.data] != null,
                    ).length;

                    return (
                      <motion.div
                        key={`result-${i}`}
                        className="batch-page__result-card glass-card"
                        variants={staggerItem}
                        whileHover={{ scale: 1.01 }}
                        style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}
                      >
                        <span className="batch-page__result-card-filename" style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {meta.icon} {res.filename}
                        </span>
                        <span className="batch-page__result-card-type" style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: 500 }}>
                          {meta.label}
                        </span>
                        <span className="batch-page__result-card-fields" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {fieldCount} fields extracted
                        </span>
                      </motion.div>
                    );
                  })}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </PageContainer>
    </motion.div>
  );
};
export default BatchPage;
