/**
 * Native WebSocket Client Hook for Real-time Communication
 * Provides connection management, message handling, and query processing
 * Modified to use native WebSocket API instead of Socket.IO
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  WebSocketConnectionState,
  WebSocketMessageType,
  WebSocketMessage,
  SystemMessage,
  QueryMessage,
  QueryProgressMessage,
  QueryResultMessage,
  QueryErrorMessage,
  QueryState,
  QueryProgressStatus,
  UseWebSocketReturn,
  WebSocketClientState,
  WebSocketClientConfig
} from '@/types/websocket';
import { useDatabaseContext } from './useDatabaseContext';

// Default configuration
const DEFAULT_CONFIG: WebSocketClientConfig = {
  url: process.env.NEXT_PUBLIC_BACKEND_URL || 'ws://localhost:8000',
  user_id: 'default_user',
  reconnectInterval: 1000,
  maxReconnectAttempts: 5,
  pingInterval: 30000,
  connectionTimeout: 10000
};

export function useWebSocketClient(config?: Partial<WebSocketClientConfig>): UseWebSocketReturn {
  // Merge with default config using useMemo
  const fullConfig = useMemo(() => ({ ...DEFAULT_CONFIG, ...config }), [config]);

  // State management
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>(
    WebSocketConnectionState.DISCONNECTED
  );
  const [queryStates, setQueryStates] = useState<Map<string, QueryState>>(new Map());
  const [clientState, setClientState] = useState<WebSocketClientState>({
    connectionState: WebSocketConnectionState.DISCONNECTED,
    isConnected: false,
    lastError: null,
    reconnectAttempts: 0,
    isReconnecting: false,
    metrics: {
      messagesSent: 0,
      messagesReceived: 0,
      totalQueries: 0,
      activeQueries: 0,
      averageLatency: 0,
      connectionUptime: 0
    }
  });

  // Get database context
  const { currentDatabaseId } = useDatabaseContext();

  // Refs
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const connectionStartTimeRef = useRef<number | null>(null);

  // Update connection state
  const updateConnectionState = useCallback((newState: WebSocketConnectionState) => {
    setConnectionState(newState);
    setClientState(prev => ({
      ...prev,
      connectionState: newState,
      isConnected: newState === WebSocketConnectionState.CONNECTED
    }));
  }, []);

  // Update metrics
  const updateMetrics = useCallback((update: Partial<WebSocketClientState['metrics']>) => {
    setClientState(prev => ({
      ...prev,
      metrics: { ...prev.metrics, ...update }
    }));
  }, []);

  // Generate unique query ID
  const generateQueryId = useCallback(() => {
    return `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Update metrics
      updateMetrics({ messagesReceived: clientState.metrics.messagesReceived + 1 });

      switch (message.type) {
        case WebSocketMessageType.SYSTEM:
          const systemMsg = message as SystemMessage;
          console.log('System message:', systemMsg.data.message);
          break;

        case WebSocketMessageType.QUERY_PROGRESS:
          const progressMsg = message as QueryProgressMessage;
          setQueryStates(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(progressMsg.query_id) || {
              id: progressMsg.query_id,
              status: QueryProgressStatus.PENDING,
              currentStep: 0,
              totalSteps: progressMsg.data.total_steps || 4,
              progress: 0,
              message: '',
              startTime: Date.now(),
              estimatedTimeRemaining: null,
              error: null
            };

            newMap.set(progressMsg.query_id, {
              ...existing,
              status: progressMsg.data.status,
              currentStep: progressMsg.data.current_step,
              progress: progressMsg.data.progress,
              message: progressMsg.data.message,
              estimatedTimeRemaining: progressMsg.data.estimated_time_remaining || null
            });

            return newMap;
          });
          break;

        case WebSocketMessageType.QUERY_RESULT:
          const resultMsg = message as QueryResultMessage;
          setQueryStates(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(resultMsg.query_id);
            if (existing) {
              newMap.set(resultMsg.query_id, {
                ...existing,
                status: QueryProgressStatus.COMPLETED,
                progress: 100,
                result: resultMsg.data,
                endTime: Date.now()
              });
            }
            return newMap;
          });

          // Update active queries count
          updateMetrics({ activeQueries: Math.max(0, clientState.metrics.activeQueries - 1) });
          break;

        case WebSocketMessageType.QUERY_ERROR:
          const errorMsg = message as QueryErrorMessage;
          setQueryStates(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(errorMsg.query_id);
            if (existing) {
              newMap.set(errorMsg.query_id, {
                ...existing,
                status: QueryProgressStatus.ERROR,
                error: errorMsg.data.error,
                endTime: Date.now()
              });
            }
            return newMap;
          });

          // Update active queries count
          updateMetrics({ activeQueries: Math.max(0, clientState.metrics.activeQueries - 1) });
          break;

        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }, [clientState.metrics, updateMetrics]);

  // Send message through WebSocket
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
      updateMetrics({ messagesSent: clientState.metrics.messagesSent + 1 });
      return true;
    }
    return false;
  }, [clientState.metrics, updateMetrics]);

  // Send query
  const sendQuery = useCallback((query: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const queryId = generateQueryId();
      const message: QueryMessage = {
        type: WebSocketMessageType.QUERY,
        query_id: queryId,
        timestamp: Date.now(),
        data: {
          query,
          database_id: currentDatabaseId || 'default'
        }
      };

      if (sendMessage(message)) {
        // Initialize query state
        setQueryStates(prev => {
          const newMap = new Map(prev);
          newMap.set(queryId, {
            id: queryId,
            status: QueryProgressStatus.PENDING,
            currentStep: 0,
            totalSteps: 4,
            progress: 0,
            message: 'Query submitted...',
            startTime: Date.now(),
            estimatedTimeRemaining: null,
            error: null
          });
          return newMap;
        });

        // Update metrics
        updateMetrics({ 
          totalQueries: clientState.metrics.totalQueries + 1,
          activeQueries: clientState.metrics.activeQueries + 1
        });

        return queryId;
      }
    }
    return null;
  }, [currentDatabaseId, generateQueryId, sendMessage, clientState.metrics, updateMetrics]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.CONNECTING || 
        socketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    updateConnectionState(WebSocketConnectionState.CONNECTING);

    try {
      // Convert HTTP/HTTPS URL to WS/WSS
      const wsUrl = fullConfig.url.replace(/^http/, 'ws');
      const fullUrl = `${wsUrl}/ws/chat/${fullConfig.user_id}`;
      
      socketRef.current = new WebSocket(fullUrl);

      socketRef.current.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionState(WebSocketConnectionState.CONNECTED);
        connectionStartTimeRef.current = Date.now();
        
        // Reset reconnect attempts
        setClientState(prev => ({
          ...prev,
          reconnectAttempts: 0,
          isReconnecting: false,
          lastError: null
        }));

        // Start ping interval
        if (fullConfig.pingInterval > 0) {
          pingIntervalRef.current = setInterval(() => {
            if (socketRef.current?.readyState === WebSocket.OPEN) {
              socketRef.current.ping?.();
            }
          }, fullConfig.pingInterval);
        }
      };

      socketRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionState(WebSocketConnectionState.DISCONNECTED);
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt reconnection if enabled
        if (fullConfig.reconnect) {
          reconnect();
        }
      };

      socketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setClientState(prev => ({
          ...prev,
          lastError: 'Connection error occurred'
        }));
        updateConnectionState(WebSocketConnectionState.ERROR);
      };

      socketRef.current.onmessage = handleMessage;

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setClientState(prev => ({
        ...prev,
        lastError: 'Failed to establish connection'
      }));
      updateConnectionState(WebSocketConnectionState.ERROR);
    }
  }, [fullConfig, updateConnectionState, handleMessage]);

  // Reconnect logic
  const reconnect = useCallback(() => {
    if (clientState.reconnectAttempts >= fullConfig.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      setClientState(prev => ({ ...prev, isReconnecting: false }));
      return;
    }

    const delay = Math.min(
      fullConfig.reconnectInterval * Math.pow(2, clientState.reconnectAttempts),
      fullConfig.maxReconnectInterval
    );

    setClientState(prev => ({ 
      ...prev, 
      isReconnecting: true,
      reconnectAttempts: prev.reconnectAttempts + 1 
    }));

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [clientState.reconnectAttempts, fullConfig.maxReconnectAttempts, fullConfig.reconnectInterval, fullConfig.maxReconnectInterval, connect]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    // Clear timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    // Close WebSocket
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    updateConnectionState(WebSocketConnectionState.DISCONNECTED);
    setClientState(prev => ({
      ...prev,
      isReconnecting: false,
      reconnectAttempts: 0
    }));
  }, [updateConnectionState]);

  // Get query state
  const getQueryState = useCallback((queryId: string): QueryState | null => {
    return queryStates.get(queryId) || null;
  }, [queryStates]);

  // Clear query state
  const clearQueryState = useCallback((queryId: string) => {
    setQueryStates(prev => {
      const newMap = new Map(prev);
      newMap.delete(queryId);
      return newMap;
    });
  }, []);

  // Update connection uptime
  useEffect(() => {
    if (connectionState === WebSocketConnectionState.CONNECTED && connectionStartTimeRef.current) {
      const interval = setInterval(() => {
        const uptime = Date.now() - (connectionStartTimeRef.current || 0);
        updateMetrics({ connectionUptime: uptime });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [connectionState, updateMetrics]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // Connection management
    connect,
    disconnect,
    
    // State
    connectionState,
    isConnected: connectionState === WebSocketConnectionState.CONNECTED,
    clientState,
    
    // Query management
    sendQuery,
    getQueryState,
    clearQueryState,
    queryStates: Array.from(queryStates.values()),
    
    // Message sending
    sendMessage
  };
}
