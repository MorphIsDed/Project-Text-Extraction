// ============================================================
// Component — DropZone (Drag & Drop File Upload)
// ============================================================

import { useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileUp } from 'lucide-react';
import './DropZone.css';

interface DropZoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}

interface Ripple {
  id: number;
  x: number;
  y: number;
}

let rippleCounter = 0;

export function DropZone({ onFileSelect, accept, disabled = false }: DropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const zoneRef = useRef<HTMLDivElement>(null);

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragActive(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only deactivate if we actually left the zone
    if (e.currentTarget === e.target) {
      setIsDragActive(false);
    }
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragActive(true);
    },
    [disabled]
  );

  const spawnRipple = useCallback((clientX: number, clientY: number) => {
    if (!zoneRef.current) return;
    const rect = zoneRef.current.getBoundingClientRect();
    const x = clientX - rect.left - 100;
    const y = clientY - rect.top - 100;
    const id = ++rippleCounter;

    setRipples((prev) => [...prev, { id, x, y }]);
    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== id));
    }, 700);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);

      if (disabled) return;

      spawnRipple(e.clientX, e.clientY);

      const files = e.dataTransfer.files;
      if (files && files[0]) {
        onFileSelect(files[0]);
      }
    },
    [disabled, onFileSelect, spawnRipple]
  );

  const handleClick = useCallback(() => {
    if (!disabled) {
      inputRef.current?.click();
    }
  }, [disabled]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files[0]) {
        onFileSelect(files[0]);
      }
      // Reset so the same file can be re-selected
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    },
    [onFileSelect]
  );

  const zoneClassNames = [
    'dropzone',
    isDragActive && 'dropzone--active',
    disabled && 'dropzone--disabled',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <motion.div
      ref={zoneRef}
      className={zoneClassNames}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
      initial={{ opacity: 0, y: 24, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      whileHover={disabled ? undefined : { scale: 1.005 }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="File upload drop zone. Drag and drop a file or click to browse."
      aria-disabled={disabled}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {/* Gradient border glow */}
      <div className="dropzone__border-glow" aria-hidden="true" />

      {/* Icon */}
      <motion.div
        className="dropzone__icon-wrapper"
        animate={isDragActive ? { scale: 1.15, y: -8 } : { scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      >
        <AnimatePresence mode="wait">
          {isDragActive ? (
            <motion.div
              key="fileup"
              initial={{ scale: 0, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0, rotate: 45 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex' }}
            >
              <FileUp className="dropzone__icon" />
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex' }}
            >
              <Upload className="dropzone__icon" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Text */}
      <div className="dropzone__text">
        <motion.p
          className="dropzone__title"
          animate={isDragActive ? { scale: 1.02 } : { scale: 1 }}
          transition={{ type: 'spring', stiffness: 400 }}
        >
          {isDragActive ? 'Drop your file here' : 'Drag and drop your file here'}
        </motion.p>
        <p className="dropzone__subtitle">
          or <em>click to browse</em>
        </p>
        <p className="dropzone__formats">
          PDF, JPG, PNG, BMP, TIFF, WEBP • Max 10 MB
        </p>
      </div>

      {/* Ripple effects */}
      <AnimatePresence>
        {ripples.map((ripple) => (
          <motion.div
            key={ripple.id}
            className="dropzone__ripple"
            style={{ left: ripple.x, top: ripple.y }}
            initial={{ scale: 0, opacity: 0.6 }}
            animate={{ scale: 2.5, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
            aria-hidden="true"
          />
        ))}
      </AnimatePresence>

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        className="dropzone__input"
        accept={accept}
        onChange={handleInputChange}
        disabled={disabled}
        tabIndex={-1}
        aria-hidden="true"
      />
    </motion.div>
  );
}
