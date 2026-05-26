// ============================================================
// HistoryPage — Processing History Page
// ============================================================

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, RefreshCw, Calendar, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { ResultsPanel } from '@/components/results/ResultsPanel';
import { ProgressBar } from '@/components/progress/ProgressBar';
import { listTasks, getTaskResult } from '@/api/client';
import type { TaskListItem, ExtractedDocument } from '@/api/types';
import { formatDate } from '@/utils/formatters';
import './HistoryPage.css';

type FilterType = 'all' | 'completed' | 'processing' | 'failed';

export const HistoryPage: React.FC = () => {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  
  // Keep track of expanded tasks and their fetched results
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [expandedResults, setExpandedResults] = useState<Record<string, { data: ExtractedDocument; raw: Record<string, unknown> }>>({});
  const [loadingResultId, setLoadingResultId] = useState<string | null>(null);

  const fetchTasks = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    
    try {
      const response = await listTasks();
      setTasks(response.tasks || []);
    } catch (err) {
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Poll in-progress tasks on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTasks();

    const interval = setInterval(() => {
      // If there are processing/pending tasks, let's auto-refresh
      const activeTasks = tasks.some(t => t.status === 'processing' || t.status === 'pending');
      if (activeTasks) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTasks();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchTasks, tasks]);

  const handleRefresh = () => {
    fetchTasks(true);
  };

  const handleToggleExpand = async (taskId: string, status: string) => {
    if (expandedTaskId === taskId) {
      setExpandedTaskId(null);
      return;
    }

    if (status !== 'completed') {
      return; // Only completed tasks can be expanded to show extraction results
    }

    setExpandedTaskId(taskId);

    // Fetch details if not cached yet
    if (!expandedResults[taskId]) {
      setLoadingResultId(taskId);
      try {
        const response = await getTaskResult(taskId);
        if (response.extracted_data) {
          setExpandedResults((prev) => ({
            ...prev,
            [taskId]: {
              data: response.extracted_data!,
              raw: response.extracted_data as unknown as Record<string, unknown>, // Or raw response if available
            },
          }));
        }
      } catch (err) {
        console.error('Error fetching task results:', err);
      } finally {
        setLoadingResultId(null);
      }
    }
  };

  // Compute counts
  const counts = {
    all: tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    processing: tasks.filter((t) => t.status === 'processing' || t.status === 'pending').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  };

  // Filter tasks
  const filteredTasks = tasks.filter((task) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'completed') return task.status === 'completed';
    if (activeFilter === 'failed') return task.status === 'failed';
    if (activeFilter === 'processing') return task.status === 'processing' || task.status === 'pending';
    return true;
  });

  return (
    <PageContainer
      title="Processing History"
      subtitle="View all previously processed documents and their extraction details"
    >
      <div className="history-header">
        <div className="history-filters" role="tablist" aria-label="Filter tasks by status">
          {(['all', 'completed', 'processing', 'failed'] as FilterType[]).map((filter) => (
            <button
              key={filter}
              role="tab"
              aria-selected={activeFilter === filter}
              className={`history-filters__tab ${activeFilter === filter ? 'history-filters__tab--active' : ''}`}
              onClick={() => setActiveFilter(filter)}
            >
              <span style={{ textTransform: 'capitalize' }}>{filter}</span>
              <span className="history-filters__count">{counts[filter]}</span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          className={`history-header__refresh ${refreshing ? 'history-header__refresh--spinning' : ''}`}
          disabled={loading || refreshing}
        >
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <Loader2 className="animate-spin text-accent-blue" size={32} />
        </div>
      ) : filteredTasks.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="history-empty premium-card"
        >
          <Clock className="history-empty__icon" />
          <h3 className="history-empty__title">No documents found</h3>
          <p className="history-empty__text">
            {activeFilter === 'all'
              ? "You haven't uploaded any documents yet. Go back to Home or Batch Upload to process some."
              : `There are no documents in the "${activeFilter}" state at the moment.`}
          </p>
        </motion.div>
      ) : (
        <motion.div
          className="history-grid"
          variants={{
            show: { transition: { staggerChildren: 0.05 } },
          }}
          initial="hidden"
          animate="show"
        >
          {filteredTasks.map((task) => {
            const isExpanded = expandedTaskId === task.task_id;
            const hasResult = expandedResults[task.task_id];
            const isLoadingResult = loadingResultId === task.task_id;

            return (
              <motion.div
                key={task.task_id}
                variants={{
                  hidden: { opacity: 0, y: 15 },
                  show: { opacity: 1, y: 0 },
                }}
                className="history-card premium-card"
                onClick={() => handleToggleExpand(task.task_id, task.status)}
              >
                <div className="history-card__top">
                  <div className="history-card__title-group">
                    <h3 className="history-card__filename">{task.filename}</h3>
                    <div className="history-card__meta">
                      <span className="history-card__date">
                        <Calendar size={12} />
                        {formatDate(task.created_at)}
                      </span>
                    </div>
                  </div>

                  <div className="history-card__badges">
                    {task.status === 'completed' && hasResult && (
                      <span className="status-pill status-pill--completed">
                        {hasResult.data.document_type}
                      </span>
                    )}
                    <span className={`status-pill status-pill--${task.status}`}>
                      {task.status}
                    </span>
                    {task.status === 'completed' && (
                      isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                    )}
                  </div>
                </div>

                {/* Progress bar for ongoing processing */}
                {(task.status === 'processing' || task.status === 'pending') && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <ProgressBar progress={task.progress} label={`Processing... ${task.progress}%`} showPercentage />
                  </div>
                )}

                {/* Expanded Details Pane */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="history-card__expanded"
                      onClick={(e) => e.stopPropagation()} // stop click bubbling
                    >
                      {isLoadingResult ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '1rem 0' }}>
                          <Loader2 className="animate-spin" size={18} />
                          <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Loading extracted data...</span>
                        </div>
                      ) : hasResult ? (
                        <ResultsPanel
                          data={hasResult.data}
                          rawJson={hasResult.raw}
                          downloadUrl={`/api/tasks/result/${task.task_id}`}
                        />
                      ) : (
                        <div style={{ padding: '1rem 0', color: 'var(--text-muted)' }}>
                          Failed to load task details. Please try again.
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </PageContainer>
  );
};
