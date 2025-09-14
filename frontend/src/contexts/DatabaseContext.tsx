"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

// Database context types
export interface DatabaseInfo {
  name: string;
  charset: string;
  collation: string;
  accessible: boolean;
}

export interface DatabaseContext {
  database_name: string;
  schema_initialized: boolean;
  total_tables: number;
  table_names: string[];
  selected_at: string;
  session_id: string;
}

// Context state interface
interface DatabaseContextState {
  // Current database context
  selectedDatabase: DatabaseInfo | null;
  databaseContext: DatabaseContext | null;
  sessionId: string | null;
  
  // Available databases
  availableDatabases: DatabaseInfo[];
  
  // Loading states
  isLoadingDatabases: boolean;
  isSelectingDatabase: boolean;
  
  // Error state
  error: string | null;
  
  // Actions
  fetchDatabases: () => Promise<void>;
  selectDatabase: (databaseName: string) => Promise<void>;
  clearDatabaseContext: () => void;
  refreshDatabaseContext: () => Promise<void>;
}

// Create context
const DatabaseContext = createContext<DatabaseContextState | undefined>(undefined);

// Provider component props
interface DatabaseContextProviderProps {
  children: ReactNode;
}

// Provider component
export const DatabaseContextProvider: React.FC<DatabaseContextProviderProps> = ({ children }) => {
  // State
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseInfo | null>(null);
  const [databaseContext, setDatabaseContext] = useState<DatabaseContext | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [availableDatabases, setAvailableDatabases] = useState<DatabaseInfo[]>([]);
  const [isLoadingDatabases, setIsLoadingDatabases] = useState(false);
  const [isSelectingDatabase, setIsSelectingDatabase] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generate or retrieve session ID
  const initializeSession = useCallback(() => {
    let currentSessionId = sessionStorage.getItem('ai_cfo_session_id');
    if (!currentSessionId) {
      currentSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('ai_cfo_session_id', currentSessionId);
    }
    setSessionId(currentSessionId);
    return currentSessionId;
  }, []);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
    
    // Try to load existing database context from sessionStorage
    const storedContext = sessionStorage.getItem('ai_cfo_database_context');
    if (storedContext) {
      try {
        const parsedContext = JSON.parse(storedContext);
        setDatabaseContext(parsedContext);
        setSelectedDatabase({
          name: parsedContext.database_name,
          charset: 'utf8mb4',
          collation: 'utf8mb4_general_ci',
          accessible: true
        });
      } catch (e) {
        console.warn('Failed to parse stored database context:', e);
        sessionStorage.removeItem('ai_cfo_database_context');
      }
    }
  }, [initializeSession]);

  // Fetch available databases
  const fetchDatabases = useCallback(async () => {
    setIsLoadingDatabases(true);
    setError(null);

    try {
      const response = await fetch('/api/database/list');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch databases: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setAvailableDatabases(data.databases || []);
      } else {
        throw new Error('Failed to fetch database list');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch databases';
      setError(errorMessage);
      console.error('Database fetch error:', err);
    } finally {
      setIsLoadingDatabases(false);
    }
  }, []);

  // Select database and initialize context
  const selectDatabase = useCallback(async (databaseName: string) => {
    setIsSelectingDatabase(true);
    setError(null);

    if (!sessionId) {
      setError('No session ID available');
      setIsSelectingDatabase(false);
      return;
    }

    try {
      const response = await fetch('/api/database/select', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          database_name: databaseName,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to select database: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        // Create database context
        const newDatabaseContext: DatabaseContext = {
          database_name: databaseName,
          schema_initialized: data.schema_initialized,
          total_tables: data.total_tables,
          table_names: data.tables?.map((table: { name?: string; table_name?: string }) => table.name || table.table_name) || [],
          selected_at: new Date().toISOString(),
          session_id: data.session_id || sessionId,
        };

        // Update state
        setDatabaseContext(newDatabaseContext);
        
        const selectedDb = availableDatabases.find(db => db.name === databaseName) || {
          name: databaseName,
          charset: 'utf8mb4',
          collation: 'utf8mb4_general_ci',
          accessible: true
        };
        setSelectedDatabase(selectedDb);

        // Store in sessionStorage for persistence
        sessionStorage.setItem('ai_cfo_database_context', JSON.stringify(newDatabaseContext));
        sessionStorage.setItem('ai_cfo_session_id', newDatabaseContext.session_id);

        console.log('Database selected successfully:', databaseName);
      } else {
        throw new Error('Failed to initialize database schema');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to select database';
      setError(errorMessage);
      console.error('Database selection error:', err);
    } finally {
      setIsSelectingDatabase(false);
    }
  }, [sessionId, availableDatabases]);

  // Clear database context
  const clearDatabaseContext = useCallback(() => {
    setSelectedDatabase(null);
    setDatabaseContext(null);
    setError(null);
    
    // Clear from sessionStorage
    sessionStorage.removeItem('ai_cfo_database_context');
    
    console.log('Database context cleared');
  }, []);

  // Refresh database context from backend
  const refreshDatabaseContext = useCallback(async () => {
    if (!sessionId) {
      console.warn('No session ID available for context refresh');
      return;
    }

    try {
      const response = await fetch(`/api/database/context/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to refresh context: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success && data.context_available) {
        setDatabaseContext(data.database_context);
        
        // Update selected database info
        if (data.database_context?.database_name) {
          const selectedDb = availableDatabases.find(
            db => db.name === data.database_context.database_name
          ) || {
            name: data.database_context.database_name,
            charset: 'utf8mb4',
            collation: 'utf8mb4_general_ci',
            accessible: true
          };
          setSelectedDatabase(selectedDb);
        }

        // Update sessionStorage
        sessionStorage.setItem('ai_cfo_database_context', JSON.stringify(data.database_context));
        
        console.log('Database context refreshed');
      } else {
        // No context available - clear local state
        clearDatabaseContext();
      }
    } catch (err) {
      console.error('Failed to refresh database context:', err);
      // Don't set error state for refresh failures
    }
  }, [sessionId, availableDatabases, clearDatabaseContext]);

  // Context value
  const contextValue: DatabaseContextState = {
    selectedDatabase,
    databaseContext,
    sessionId,
    availableDatabases,
    isLoadingDatabases,
    isSelectingDatabase,
    error,
    fetchDatabases,
    selectDatabase,
    clearDatabaseContext,
    refreshDatabaseContext,
  };

  return (
    <DatabaseContext.Provider value={contextValue}>
      {children}
    </DatabaseContext.Provider>
  );
};

// Custom hook to use database context
export const useDatabaseContext = () => {
  const context = useContext(DatabaseContext);
  
  if (context === undefined) {
    throw new Error('useDatabaseContext must be used within a DatabaseContextProvider');
  }
  
  return context;
};

// Export types for external use
export type { DatabaseContextState };
