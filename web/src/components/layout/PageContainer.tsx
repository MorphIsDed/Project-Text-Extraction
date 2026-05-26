// ============================================================
// Component — PageContainer (Page Layout Wrapper)
// ============================================================

import { motion } from 'framer-motion';
import './PageContainer.css';

interface PageContainerProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

const pageVariants = {
  initial: { opacity: 0, y: 24 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: 'easeOut' as const,
      staggerChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    y: -16,
    transition: { duration: 0.25, ease: 'easeIn' as const },
  },
};

const headerVariants = {
  initial: { opacity: 0, y: 16 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' as const },
  },
};

const contentVariants = {
  initial: { opacity: 0, y: 12 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, delay: 0.15, ease: 'easeOut' as const },
  },
};

export function PageContainer({ title, subtitle, children }: PageContainerProps) {
  return (
    <motion.main
      className="page-container"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <motion.div className="page-container__header" variants={headerVariants}>
        <h1 className="page-container__title">{title}</h1>
        {subtitle && (
          <p className="page-container__subtitle">{subtitle}</p>
        )}
      </motion.div>

      <motion.div className="page-container__content" variants={contentVariants}>
        {children}
      </motion.div>
    </motion.main>
  );
}
