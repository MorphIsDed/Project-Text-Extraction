import { motion, AnimatePresence } from 'framer-motion';
import { Upload, ScanSearch, FileOutput, CheckCircle2, XCircle } from 'lucide-react';
import './ProcessingSteps.css';

interface ProcessingStepsProps {
  currentStep: number; // 0-3
  status: 'idle' | 'processing' | 'completed' | 'failed';
}

const STEPS = [
  { label: 'Upload', Icon: Upload },
  { label: 'Classify', Icon: ScanSearch },
  { label: 'Extract', Icon: FileOutput },
  { label: 'Complete', Icon: CheckCircle2 },
] as const;

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.12, delayChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.85 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 260, damping: 20 },
  },
};

const connectorVariants = {
  hidden: { opacity: 0, scaleX: 0.5 },
  visible: {
    opacity: 1,
    scaleX: 1,
    transition: { type: 'spring' as const, stiffness: 180, damping: 22 },
  },
};

function StepCircle({
  stepIndex,
  currentStep,
  status,
  Icon,
}: {
  stepIndex: number;
  currentStep: number;
  status: ProcessingStepsProps['status'];
  Icon: typeof Upload;
}) {
  const isCompleted = stepIndex < currentStep || (status === 'completed' && stepIndex <= currentStep);
  const isActive = stepIndex === currentStep && status === 'processing';
  const isFailed = stepIndex === currentStep && status === 'failed';
  const isUpcoming = !isCompleted && !isActive && !isFailed;

  let circleClass = 'processing-steps__circle';
  if (isCompleted) circleClass += ' processing-steps__circle--completed';
  else if (isActive) circleClass += ' processing-steps__circle--active';
  else if (isFailed) circleClass += ' processing-steps__circle--failed';
  else if (isUpcoming) circleClass += ' processing-steps__circle--upcoming';

  return (
    <motion.div
      className={circleClass}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.95 }}
      aria-label={`Step ${stepIndex + 1}: ${(STEPS[stepIndex as 0 | 1 | 2 | 3] || { label: '' }).label} – ${
        isCompleted ? 'completed' : isActive ? 'in progress' : isFailed ? 'failed' : 'upcoming'
      }`}
    >
      {/* Glow ring for active step */}
      {isActive && <span className="processing-steps__glow" />}

      <AnimatePresence mode="wait">
        {isCompleted ? (
          <motion.svg
            key="check"
            className="processing-steps__checkmark"
            viewBox="0 0 24 24"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
          >
            <path
              className="processing-steps__checkmark-path"
              d="M5 13l4 4L19 7"
            />
          </motion.svg>
        ) : isFailed ? (
          <motion.div
            key="fail"
            initial={{ scale: 0, rotate: -90 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
          >
            <XCircle size={20} />
          </motion.div>
        ) : (
          <motion.div
            key="icon"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Icon size={20} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export function ProcessingSteps({ currentStep, status }: ProcessingStepsProps) {
  return (
    <motion.div
      className="processing-steps"
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={0}
      aria-valuemax={3}
      aria-label="Document processing progress"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {STEPS.map((step, index) => {
        // Determine label modifier class
        const isCompleted =
          index < currentStep || (status === 'completed' && index <= currentStep);
        const isActive = index === currentStep && status === 'processing';
        const isFailed = index === currentStep && status === 'failed';

        let labelClass = 'processing-steps__label';
        if (isCompleted) labelClass += ' processing-steps__label--completed';
        else if (isActive) labelClass += ' processing-steps__label--active';
        else if (isFailed) labelClass += ' processing-steps__label--failed';

        // Connector fill width
        const connectorFill = (() => {
          if (index >= STEPS.length - 1) return 0; // No connector after last
          const nextIdx = index + 1;
          if (nextIdx < currentStep) return 100;
          if (nextIdx === currentStep && status === 'processing') return 50;
          if (nextIdx <= currentStep && status === 'completed') return 100;
          return 0;
        })();

        return (
          <motion.div key={step.label} style={{ display: 'contents' }}>
            {/* Step item: circle + label */}
            <motion.div className="processing-steps__item" variants={itemVariants}>
              <StepCircle
                stepIndex={index}
                currentStep={currentStep}
                status={status}
                Icon={step.Icon}
              />
              <span className={labelClass}>{step.label}</span>
            </motion.div>

            {/* Connector line (not after last step) */}
            {index < STEPS.length - 1 && (
              <motion.div className="processing-steps__connector" variants={connectorVariants}>
                <div className="processing-steps__line">
                  <motion.div
                    className="processing-steps__line-fill"
                    initial={{ width: '0%' }}
                    animate={{ width: `${connectorFill}%` }}
                    transition={{ type: 'spring' as const, stiffness: 120, damping: 18 }}
                  />
                </div>
              </motion.div>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
}
