/**
 * WebSocket Query Hook
 * Handles BI query processing through WebSocket connection
 */
"use client";

import { useState, useCallback, useRef } from 'react';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

export interface QueryRequest {
  query: string;
  session_id?: string;
  database_context?: {
    database: string;
  };
  preferences?: {
    output_format?: string;
  };
}

export interface DatabaseSelectionRequest {
  database_name: string;
  session_id?: string;
}

export interface QueryResponse {
  type: string;
  response?: {
    query_id?: string;
    intent?: Record<string, unknown>;
    data?: unknown[];
    visualization?: Record<string, unknown>;
    success?: boolean;
  };
  error?: {
    error_type: string;
    message: string;
    suggestions?: string[];
  };
  correlation_id?: string;
  timestamp: string;
}

export interface DatabaseInfo {
  name: string;
  charset?: string;
  collation?: string;
  accessible?: boolean;
}

export interface DatabaseResponse {
  databases?: DatabaseInfo[];
  response?: {
    success?: boolean;
    database_name?: string;
    session_id?: string;
    table_count?: number;
    message?: string;
  };
  error?: {
    error_type: string;
    message: string;
  };
  correlation_id?: string;
  timestamp: string;
}

export const useWebSocketQuery = () => {
  const { isConnected, getConnection } = useGlobalWebSocket();
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);
  const pendingRequestsRef = useRef<Map<string, {
    resolve: (value: QueryResponse | DatabaseResponse) => void;
    reject: (reason: Error) => void;
    timeout: NodeJS.Timeout;
  }>>(new Map());

  const generateCorrelationId = useCallback(() => {
    return `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  const sendMessage = useCallback(async (
    message: Record<string, unknown>,
    timeoutMs: number = 30000
  ): Promise<QueryResponse | DatabaseResponse> => {
    if (!isConnected) {
      throw new Error('WebSocket not connected');
    }

    const socket = getConnection();
    if (!socket) {
      throw new Error('WebSocket connection not available');
    }

    const correlationId = generateCorrelationId();
    const messageWithId = {
      ...message,
      correlation_id: correlationId,
      timestamp: new Date().toISOString()
    };

    return new Promise((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        pendingRequestsRef.current.delete(correlationId);
        reject(new Error(`Request timeout after ${timeoutMs}ms`));
      }, timeoutMs);

      // Store the promise resolvers
      pendingRequestsRef.current.set(correlationId, {
        resolve,
        reject,
        timeout
      });

      // Set up message listener
      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          const responseCorrelationId = response.correlation_id;

          if (responseCorrelationId && pendingRequestsRef.current.has(responseCorrelationId)) {
            const pendingRequest = pendingRequestsRef.current.get(responseCorrelationId)!;
            clearTimeout(pendingRequest.timeout);
            pendingRequestsRef.current.delete(responseCorrelationId);

            // Update last response state
            setLastResponse(response);

            // Check for errors
            if (response.type.includes('_error') || response.error) {
              pendingRequest.reject(new Error(response.error?.message || 'Request failed'));
            } else {
              pendingRequest.resolve(response);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      // Add message listener
      socket.addEventListener('message', handleMessage);

      // Send the message
      try {
        socket.send(JSON.stringify(messageWithId));
        console.log('WebSocketQuery: Sent message:', messageWithId.type);
      } catch (error) {
        clearTimeout(timeout);
        pendingRequestsRef.current.delete(correlationId);
        socket.removeEventListener('message', handleMessage);
        reject(error);
      }

      // Clean up listener after timeout (in case no response comes)
      setTimeout(() => {
        socket.removeEventListener('message', handleMessage);
      }, timeoutMs + 1000);
    });
  }, [isConnected, getConnection, generateCorrelationId]);

  const processQuery = useCallback(async (
    queryRequest: QueryRequest
  ): Promise<QueryResponse> => {
    setIsProcessing(true);
    
    try {
      console.log('WebSocketQuery: Processing query:', queryRequest.query);
      
      const response = await sendMessage({
        type: 'query',
        ...queryRequest
      });

      console.log('WebSocketQuery: Query response received:', response.type);
      return response;
    } catch (error) {
      console.error('WebSocketQuery: Query processing failed:', error);
      const errorResponse: QueryResponse = {
        type: 'query_error',
        error: {
          error_type: 'websocket_error',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        },
        timestamp: new Date().toISOString()
      };
      setLastResponse(errorResponse);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  }, [sendMessage]);

  const selectDatabase = useCallback(async (
    selectionRequest: DatabaseSelectionRequest
  ): Promise<DatabaseResponse> => {
    try {
      console.log('WebSocketQuery: Selecting database:', selectionRequest.database_name);
      
      const response = await sendMessage({
        type: 'database_select',
        ...selectionRequest
      });

      console.log('WebSocketQuery: Database selection response received:', response.type);
      return response;
    } catch (error) {
      console.error('WebSocketQuery: Database selection failed:', error);
      throw error;
    }
  }, [sendMessage]);

  const getAvailableDatabases = useCallback(async (): Promise<DatabaseResponse> => {
    try {
      console.log('WebSocketQuery: Getting available databases');
      
      const response = await sendMessage({
        type: 'get_databases'
      });

      console.log('WebSocketQuery: Databases response received:', response.type);
      return response;
    } catch (error) {
      console.error('WebSocketQuery: Get databases failed:', error);
      throw error;
    }
  }, [sendMessage]);

  const getDatabaseContext = useCallback(async (
    sessionId: string
  ): Promise<DatabaseResponse> => {
    try {
      console.log('WebSocketQuery: Getting database context for session:', sessionId);
      
      const response = await sendMessage({
        type: 'get_database_context',
        session_id: sessionId
      });

      console.log('WebSocketQuery: Database context response received:', response.type);
      return response;
    } catch (error) {
      console.error('WebSocketQuery: Get database context failed:', error);
      throw error;
    }
  }, [sendMessage]);

  const sendHeartbeat = useCallback(async (): Promise<void> => {
    try {
      await sendMessage({
        type: 'heartbeat'
      }, 5000); // Short timeout for heartbeat
      console.log('WebSocketQuery: Heartbeat sent successfully');
    } catch (error) {
      console.error('WebSocketQuery: Heartbeat failed:', error);
    }
  }, [sendMessage]);

  return {
    isConnected,
    isProcessing,
    lastResponse,
    processQuery,
    selectDatabase,
    getAvailableDatabases,
    getDatabaseContext,
    sendHeartbeat
  };
};

export default useWebSocketQuery;
