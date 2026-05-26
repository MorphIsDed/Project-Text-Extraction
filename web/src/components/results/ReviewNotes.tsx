import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Circle } from 'lucide-react';
import './ReviewNotes.css';

interface ReviewNotesProps {
  notes: string[];
  needsReview: boolean;
}

const containerVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1] as const,
      staggerChildren: 0.08,
    },
  },
  exit: {
    opacity: 0,
    y: -12,
    transition: { duration: 0.25 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -16 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] as const },
  },
};

export function ReviewNotes({ notes, needsReview }: ReviewNotesProps) {
  if (!needsReview && notes.length === 0) {
    return null;
  }

  const hasNotes = notes.length > 0;

  return (
    <AnimatePresence>
      <motion.div
        className={`review-notes ${!hasNotes ? 'review-notes--warning-only' : ''}`}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        role="alert"
        aria-label="Review notes"
      >
        <div className="review-notes__header">
          <AlertTriangle className="review-notes__icon" size={20} aria-hidden="true" />
          <h3 className="review-notes__title">Review Notes</h3>
          {hasNotes && (
            <motion.span
              className="review-notes__count"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25, delay: 0.3 }}
            >
              {notes.length}
            </motion.span>
          )}
        </div>

        {hasNotes ? (
          <ul className="review-notes__list">
            {notes.map((note, index) => (
              <motion.li
                key={index}
                className="review-notes__item"
                variants={itemVariants}
              >
                <Circle className="review-notes__bullet" size={6} fill="currentColor" aria-hidden="true" />
                <span>{note}</span>
              </motion.li>
            ))}
          </ul>
        ) : (
          <motion.p
            className="review-notes__warning-text"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            This document has been flagged for manual review.
          </motion.p>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
