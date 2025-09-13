"use client";
import React, { useState, useEffect } from "react";
import ClientOnly from "./ClientOnly";
import { ChatInterface } from "./chat/chat-interface";
import { BentoGrid } from "./bento-grid/bento-grid";
import { BentoGridCard } from "@/types/dashboard";
import { useRealData } from "@/hooks/useRealData";
import { DatabaseSetupButton } from "./database-setup-button";
import { DatabaseSelectorModal } from "./database-selector-modal";
import { motion } from "framer-motion";

function DashboardContent() {
  const {
    chatMessages,
    bentoCards,
    suggestions,
    error,
    sendMessage,
    refreshDashboard,
    clearError,
    isLoading,
    refreshSuccess,
    clearRefreshSuccess,
  } = useRealData();

  // Persistent layout state that doesn't reset on errors
  const [layoutMode, setLayoutMode] = useState<'fullwidth' | 'split'>('fullwidth');
  const [showDatabaseModal, setShowDatabaseModal] = useState(false);
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  
  // Check if user has started chatting (has sent at least one message)
  const hasUserStartedChatting = chatMessages.some(message => message.sender === "user");
  
  // Update layout mode when user starts chatting, but persist it
  useEffect(() => {
    if (hasUserStartedChatting && layoutMode === 'fullwidth') {
      setLayoutMode('split');
    }
  }, [hasUserStartedChatting, layoutMode]);

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  const handleDatabaseSetup = () => {
    setShowDatabaseModal(true);
  };

  const handleDatabaseSelected = (databaseName: string) => {
    console.log("Database selected:", databaseName);
    setSelectedDatabase(databaseName);
    // Store selected database in session storage for persistence
    sessionStorage.setItem('selected_database', databaseName);
    // Clear any cached dashboard data to force refresh with new database context
    const cacheKey = `dashboard_initial_data_${databaseName}`;
    sessionStorage.removeItem(cacheKey);
    // Refresh dashboard data after database selection and schema initialization
    refreshDashboard();
    setShowDatabaseModal(false);
  };

  const handleCardUpdate = (updatedCards: BentoGridCard[]) => {
    // For now, we don't need to handle card updates from drag/drop
    // This would be where we'd sync card positions back to the server
    console.log("Cards updated:", updatedCards);
  };

  // Error notification banner (non-blocking)
  const errorBanner = error && (
    <motion.div
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 max-w-md w-full mx-4"
    >
      <div className="corporate-card bg-red-50 border-red-200 border">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-medium text-red-800">Connection Error</h4>
              <p className="text-xs text-red-600">{error}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={refreshDashboard}
              className="text-xs px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors flex items-center gap-1"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                  Retrying...
                </>
              ) : (
                'Retry'
              )}
            </button>
            <button
              onClick={clearError}
              className="text-xs px-3 py-1 border border-red-300 text-red-700 rounded-md hover:bg-red-50 transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );

  // Success notification banner
  const successBanner = refreshSuccess && (
    <motion.div
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50"
    >
      <div className="bg-green-50 border border-green-200 rounded-lg shadow-md px-4 py-3 flex items-center gap-3 min-w-max">
        <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-medium text-green-800">Dashboard Refreshed</h4>
          <p className="text-xs text-green-600">Your data has been updated successfully</p>
        </div>
        <button
          onClick={clearRefreshSuccess}
          className="text-xs px-2 py-1 border border-green-300 text-green-700 rounded hover:bg-green-100 transition-colors flex-shrink-0"
        >
          Dismiss
        </button>
      </div>
    </motion.div>
  );

  return (
    <div className="h-screen relative" style={{ 
      background: 'linear-gradient(135deg, var(--corporate-gray-50), var(--corporate-blue-50))',
      transition: 'all var(--duration-normal) var(--ease-in-out)'
    }}>
      {/* Notification banners */}
      {errorBanner}
      {successBanner}
      
      {layoutMode === 'fullwidth' ? (
        // Initial state: Show only chat interface (full width)
        <motion.div
          key="fullwidth"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="h-full"
        >
          <ChatInterface
            messages={chatMessages}
            suggestions={suggestions}
            onSendMessage={handleSendMessage}
            isFullWidth={true}
            isLoading={isLoading}
            onDatabaseSetup={handleDatabaseSetup}
            selectedDatabase={selectedDatabase}
          />
        </motion.div>
      ) : (
        // After user starts chatting: Show split layout (30-70)
        <motion.div
          key="split"
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          className="h-full flex"
        >
          {/* Chat Interface - 30% */}
          <motion.div
            initial={{ width: "100%" }}
            animate={{ width: "30%" }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
            className="min-w-[380px] max-w-[480px] corporate-glass relative"
            style={{
              borderRight: '1px solid var(--corporate-gray-200)',
              boxShadow: 'var(--shadow-xl)'
            }}
          >
            {/* Professional sidebar accent */}
            <div 
              className="absolute left-0 top-0 bottom-0 w-1"
              style={{ background: 'linear-gradient(180deg, var(--corporate-blue-600), var(--corporate-indigo-600))' }}
            ></div>
            <ChatInterface
              messages={chatMessages}
              suggestions={suggestions}
              onSendMessage={handleSendMessage}
              isFullWidth={false}
              isLoading={isLoading}
              onDatabaseSetup={handleDatabaseSetup}
              selectedDatabase={selectedDatabase}
            />
          </motion.div>

          {/* Dashboard - 70% */}
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: "70%", opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeInOut" }}
            className="flex-1 flex flex-col overflow-hidden"
          >
            {/* Dashboard Header */}
            <motion.header
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="border-b border-gray-200 bg-white/80 backdrop-blur-sm"
              style={{ 
                padding: 'var(--space-6)',
                borderBottom: '1px solid var(--corporate-gray-200)'
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="corporate-heading-2" style={{ color: 'var(--corporate-gray-900)' }}>
                    Financial Dashboard
                  </h1>
                  <p className="corporate-body-sm" style={{ 
                    marginTop: 'var(--space-1)',
                    color: 'var(--corporate-gray-600)'
                  }}>
                    Real-time insights and analytics powered by AI
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {/* Database Setup Button */}
                  <DatabaseSetupButton 
                    variant="secondary"
                    size="sm"
                    selectedDatabase={selectedDatabase}
                    onClick={() => setShowDatabaseModal(true)}
                    onDatabaseSelected={(dbName) => {
                      setSelectedDatabase(dbName);
                      handleDatabaseSelected(dbName);
                    }}
                  />
                  
                  {/* Refresh button */}
                  <button
                    onClick={refreshDashboard}
                    className="corporate-button-secondary text-xs px-3 py-2 flex items-center gap-2"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                        Refreshing...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Refresh
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.header>
            
            {/* Dashboard Content Area */}
            <div className="flex-1 overflow-hidden">
              <div 
                className="h-full"
                style={{ padding: 'var(--space-6)' }}
              >
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                  className="h-full"
                >
                  <BentoGrid
                    cards={bentoCards}
                    onCardsUpdate={handleCardUpdate}
                  />
                </motion.div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
      
      {/* Database Selector Modal */}
      <DatabaseSelectorModal
        isOpen={showDatabaseModal}
        onClose={() => setShowDatabaseModal(false)}
        onDatabaseSelect={handleDatabaseSelected}
      />
    </div>
  );
}

export default function Dashboard() {
  return (
    <ClientOnly fallback={
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-600/20 rounded-full blur-xl"></div>
            <div className="relative w-16 h-16 mx-auto mb-6">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-16 h-16 border-4 border-slate-200 dark:border-slate-700 border-t-blue-500 rounded-full"
              />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Loading your dashboard</h3>
          <p className="text-slate-600 dark:text-slate-400">Setting up your AI CFO assistant...</p>
        </motion.div>
      </div>
    }>
      <DashboardContent />
    </ClientOnly>
  );
}