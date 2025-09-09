"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Database {
  name: string;
  charset: string;
  collation: string;
  accessible: boolean;
}

interface DatabaseSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDatabaseSelect: (databaseName: string) => void;
}

export const DatabaseSelectorModal: React.FC<DatabaseSelectorModalProps> = ({
  isOpen,
  onClose,
  onDatabaseSelect
}) => {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [selectedDatabase, setSelectedDatabase] = useState<string>("");
  const [fetchingDatabases, setFetchingDatabases] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectingDatabase, setSelectingDatabase] = useState(false);

  // Fetch databases when modal opens
  useEffect(() => {
    if (isOpen && databases.length === 0) {
      // Add debounce to prevent rapid calls
      const timeoutId = setTimeout(() => {
        fetchDatabases();
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [isOpen, databases.length]);

  const fetchDatabases = async () => {
    setFetchingDatabases(true);
    setError(null);
    
    try {
      const response = await fetch("/api/database/list");
      
      if (!response.ok) {
        throw new Error(`Failed to fetch databases: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setDatabases(data.databases || []);
      } else {
        throw new Error("Failed to fetch database list");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch databases");
    } finally {
      setFetchingDatabases(false);
    }
  };

  const handleDatabaseSelect = async () => {
    if (!selectedDatabase) return;
    
    setSelectingDatabase(true);
    setError(null);
    
    try {
      const response = await fetch("/api/database/select", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          database_name: selectedDatabase,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to select database: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        onDatabaseSelect(selectedDatabase);
        onClose();
      } else {
        throw new Error("Failed to initialize database schema");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to select database");
    } finally {
      setSelectingDatabase(false);
    }
  };

  const handleRetry = () => {
    setDatabases([]);
    setError(null);
    fetchDatabases();
  };

  const handleClose = () => {
    if (!selectingDatabase && !fetchingDatabases) {
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]"
            onClick={handleClose}
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-4 overflow-y-auto"
          >
            <div className="corporate-card w-full max-w-md bg-white/95 backdrop-blur-sm my-auto mx-auto relative shadow-2xl max-h-[90vh] overflow-hidden flex flex-col">
              {/* Header */}
              <div className="border-b border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="corporate-heading-3 text-gray-900">
                      Select Database
                    </h2>
                    <p className="corporate-body-sm text-gray-600 mt-1">
                      Choose a database to initialize the schema
                    </p>
                  </div>
                  {!selectingDatabase && !fetchingDatabases && (
                    <button
                      onClick={handleClose}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {/* Content */}
              <div className="p-6 flex-1 overflow-y-auto min-h-0">
                {/* Loading State */}
                {fetchingDatabases && (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-center">
                      <div className="w-8 h-8 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
                      <p className="corporate-body-sm text-gray-600">
                        Fetching available databases...
                      </p>
                    </div>
                  </div>
                )}

                {/* Error State */}
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                    <div className="flex items-start">
                      <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
                      </svg>
                      <div className="flex-1">
                        <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                        <p className="text-sm text-red-700 mt-1">{error}</p>
                      </div>
                    </div>
                    <div className="mt-4">
                      <button
                        onClick={handleRetry}
                        className="corporate-button-secondary text-sm"
                        disabled={fetchingDatabases}
                      >
                        Try Again
                      </button>
                    </div>
                  </div>
                )}

                {/* Database List */}
                {!fetchingDatabases && !error && databases.length > 0 && (
                  <div className="space-y-3">
                    <label className="corporate-body-sm font-medium text-gray-700">
                      Available Databases
                    </label>
                    
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {databases.map((database) => (
                        <motion.label
                          key={database.name}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className={`
                            flex items-center p-3 rounded-lg border cursor-pointer transition-all
                            ${selectedDatabase === database.name
                              ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                            }
                          `}
                        >
                          <input
                            type="radio"
                            name="database"
                            value={database.name}
                            checked={selectedDatabase === database.name}
                            onChange={(e) => setSelectedDatabase(e.target.value)}
                            className="sr-only"
                          />
                          
                          <div className="flex-1">
                            <div className="flex items-center">
                              <div className={`
                                w-2 h-2 rounded-full mr-3
                                ${database.accessible ? 'bg-green-500' : 'bg-red-500'}
                              `}></div>
                              <div>
                                <p className="corporate-body-sm font-medium text-gray-900">
                                  {database.name}
                                </p>
                                <p className="corporate-body-xs text-gray-500">
                                  {database.charset} • {database.collation}
                                </p>
                              </div>
                            </div>
                          </div>
                          
                          {selectedDatabase === database.name && (
                            <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          )}
                        </motion.label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty State */}
                {!fetchingDatabases && !error && databases.length === 0 && (
                  <div className="text-center py-8">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                    <p className="corporate-body-sm text-gray-600">No databases found</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              {!fetchingDatabases && !error && databases.length > 0 && (
                <div className="border-t border-gray-200 p-6 flex justify-end space-x-3 flex-shrink-0">
                  <button
                    onClick={handleClose}
                    className="corporate-button-secondary"
                    disabled={selectingDatabase}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDatabaseSelect}
                    disabled={!selectedDatabase || selectingDatabase}
                    className={`
                      corporate-button-primary flex items-center gap-2
                      ${(!selectedDatabase || selectingDatabase) ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    {selectingDatabase ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Initializing...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Select Database
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
