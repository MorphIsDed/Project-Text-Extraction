import { motion } from 'framer-motion';
import './ProgressBar.css';

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  showPercentage?: boolean;
}

export function ProgressBar({ progress, label, showPercentage = true }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, progress));
  const isComplete = clamped >= 100;

  return (
    <motion.div
      className="progress-bar"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header row: label + percentage */}
      {(label || showPercentage) && (
        <div className="progress-bar__header">
          {label && <span className="progress-bar__label">{label}</span>}
          {showPercentage && (
            <motion.span
              className={`progress-bar__percentage${isComplete ? ' progress-bar__percentage--complete' : ''}`}
              key={Math.round(clamped)}
              initial={{ scale: 1.3, opacity: 0.6 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              {Math.round(clamped)}%
            </motion.span>
          )}
        </div>
      )}

      {/* Track */}
      <div className="progress-bar__track" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
        {/* Animated fill */}
        <motion.div
          className={`progress-bar__fill${isComplete ? ' progress-bar__fill--complete' : ''}`}
          initial={{ width: '0%' }}
          animate={{ width: `${clamped}%` }}
          transition={{ type: 'spring', stiffness: 80, damping: 16, mass: 0.8 }}
        >
          {/* Shimmer overlay while loading */}
          {!isComplete && clamped > 0 && <div className="progress-bar__shimmer" />}
        </motion.div>
      </div>
    </motion.div>
  );
}
