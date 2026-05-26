// ============================================================
// Component — ThemeToggle (Animated Sun/Moon Toggle)
// ============================================================

import { motion, AnimatePresence } from 'framer-motion';
import { Sun, Moon } from 'lucide-react';
import './ThemeToggle.css';

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

const iconVariants = {
  initial: { scale: 0, rotate: -180, opacity: 0 },
  animate: { scale: 1, rotate: 0, opacity: 1 },
  exit: { scale: 0, rotate: 180, opacity: 0 },
};

export function ThemeToggle({ isDark, onToggle }: ThemeToggleProps) {
  return (
    <motion.div
      className="theme-toggle"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.2 }}
    >
      <motion.button
        className={`theme-toggle__track ${isDark ? 'theme-toggle__track--dark' : 'theme-toggle__track--light'}`}
        onClick={onToggle}
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        role="switch"
        aria-checked={isDark}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        type="button"
      >
        <motion.div
          className={`theme-toggle__thumb ${isDark ? 'theme-toggle__thumb--dark' : 'theme-toggle__thumb--light'}`}
          layout
          animate={{ x: isDark ? 0 : 26 }}
          transition={{
            type: 'spring',
            stiffness: 500,
            damping: 30,
          }}
        >
          <AnimatePresence mode="wait">
            {isDark ? (
              <motion.div
                key="moon"
                variants={iconVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={{ duration: 0.25 }}
                style={{ display: 'flex' }}
              >
                <Moon className="theme-toggle__icon" />
              </motion.div>
            ) : (
              <motion.div
                key="sun"
                variants={iconVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={{ duration: 0.25 }}
                style={{ display: 'flex' }}
              >
                <Sun className="theme-toggle__icon" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.button>
    </motion.div>
  );
}
