// ============================================================
// App Component — Root Layout, Router, and Page Transitions
// ============================================================

import React, { useMemo } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { HomePage } from '@/pages/HomePage';
import { BatchPage } from '@/pages/BatchPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { useTheme } from '@/hooks/useTheme';
import './App.css';

// Separate AppContent component to utilize useLocation hook inside BrowserRouter context
const AppContent: React.FC = () => {
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();

  return (
    <div className="app-layout">
      {/* Drifting Background Orbs */}
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Sticky Navigation Header */}
      <Header isDark={isDark} onToggleTheme={toggleTheme} />

      {/* Main Pages Switcher */}
      <main className="app-main">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<HomePage />} />
            <Route path="/batch" element={<BatchPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route
              path="/settings"
              element={<SettingsPage isDark={isDark} onToggleTheme={toggleTheme} />}
            />
          </Routes>
        </AnimatePresence>
      </main>

      {/* Notifications system configured for elegant, themed visuals */}
      <Toaster
        position="bottom-right"
        toastOptions={{
          className: 'premium-card',
          style: {
            background: isDark ? 'rgba(20, 20, 25, 0.85)' : 'rgba(255, 255, 255, 0.85)',
            color: isDark ? 'var(--text-primary)' : 'var(--text-primary)',
            border: '1px solid var(--surface-border)',
            backdropFilter: 'blur(12px)',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-sm)',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.2)',
          },
          duration: 4000,
        }}
      />
    </div>
  );
};

export const App: React.FC = () => {
  const queryClient = useMemo(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
      },
    },
  }), []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
};
