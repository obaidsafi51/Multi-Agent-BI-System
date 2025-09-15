/**
 * WebSocket Client Hook for Real-time Communication
 * Provides connection management, message handling, and query processing
 */

import { useState, useEffect, useRef, useCallback } from 'react';
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

// Default configuration
const DEFAULT_CONFIG: Omit<WebSocketClientConfig, 'url' | 'user_id'> = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  pingInterval: 30000,
  connectionTimeout: 10000
};

export function useWebSocketClient(
  user_id: string,
  config?: Partial<WebSocketClientConfig>
): UseWebSocketReturn {
  
  // Configuration
  const fullConfig: WebSocketClientConfig = {
    url: process.env.NEXT_PUBLIC_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`,
    user_id,
    ...DEFAULT_CONFIG,
    ...config
  };

  // State
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>(
    WebSocketConnectionState.DISCONNECTED
  );
  const [activeQueries, setActiveQueries] = useState<Map<string, QueryState>>(new Map());
  const [clientState, setClientState] = useState<WebSocketClientState>({
    connectionState: WebSocketConnectionState.DISCONNECTED,
    isConnected: false,
    reconnectAttempts: 0,
    lastPingTime: null,
    latency: null,
    metrics: {
      messagesReceived: 0,
      messagesSent: 0,
      reconnectCount: 0,
      connectionUptime: 0
    }
  });

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
  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('WebSocket message received:', message);
    
    updateMetrics({ messagesReceived: clientState.metrics.messagesReceived + 1 });

    switch (message.type) {
      case WebSocketMessageType.SYSTEM:
        console.log('System message:', (message as SystemMessage).message);
        break;

      case WebSocketMessageType.PONG:
        if (clientState.lastPingTime) {
          const latency = Date.now() - clientState.lastPingTime;
          setClientState(prev => ({ ...prev, latency, lastPingTime: null }));
        }
        break;

      case WebSocketMessageType.QUERY_PROGRESS:
        const progressMsg = message as QueryProgressMessage;
        setActiveQueries(prev => {
          const updated = new Map(prev);
          const existingQuery = updated.get(progressMsg.query_id);
          
          if (existingQuery) {
            updated.set(progressMsg.query_id, {
              ...existingQuery,
              status: progressMsg.status,
              progress: progressMsg.progress,
              current_step: progressMsg.step,
              estimated_time_remaining: progressMsg.estimated_time_remaining
            });
          }
          
          return updated;
        });
        break;

      case WebSocketMessageType.QUERY_RESULT:
        const resultMsg = message as QueryResultMessage;
        setActiveQueries(prev => {
          const updated = new Map(prev);
          const existingQuery = updated.get(resultMsg.query_id);
          
          if (existingQuery) {
            updated.set(resultMsg.query_id, {
              ...existingQuery,
              status: QueryProgressStatus.COMPLETED,
              progress: 100,
              result: resultMsg.result
            });
          }
          
          return updated;
        });
        break;

      case WebSocketMessageType.QUERY_ERROR:
        const errorMsg = message as QueryErrorMessage;
        setActiveQueries(prev => {
          const updated = new Map(prev);
          const existingQuery = updated.get(errorMsg.query_id);
          
          if (existingQuery) {
            updated.set(errorMsg.query_id, {
              ...existingQuery,
              status: QueryProgressStatus.ERROR,
              error: errorMsg.error
            });
          }
          
          return updated;
        });
        break;

      case WebSocketMessageType.METRICS:
        // Handle metrics if needed
        break;

      default:
        console.log('Unhandled message type:', message.type);
    }
  }, [clientState.lastPingTime, clientState.metrics.messagesReceived, updateMetrics]);

  // Send message
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('message', message);
      updateMetrics({ messagesSent: clientState.metrics.messagesSent + 1 });
      console.log('WebSocket message sent:', message);
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }, [clientState.metrics.messagesSent, updateMetrics]);

  // Send ping
  const sendPing = useCallback(() => {
    if (socketRef.current?.connected) {
      const pingTime = Date.now();
      setClientState(prev => ({ ...prev, lastPingTime: pingTime }));
      
      sendMessage({
        type: WebSocketMessageType.PING,
        timestamp: new Date().toISOString()
      });
    }
  }, [sendMessage]);

  // Start ping interval
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    
    pingIntervalRef.current = setInterval(sendPing, fullConfig.pingInterval);
  }, [sendPing, fullConfig.pingInterval]);

  // Stop ping interval
  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Handle reconnect
  const handleReconnect = useCallback(() => {
    if (clientState.reconnectAttempts >= fullConfig.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      updateConnectionState(WebSocketConnectionState.ERROR);
      return;
    }

    updateConnectionState(WebSocketConnectionState.RECONNECTING);
    setClientState(prev => ({ 
      ...prev, 
      reconnectAttempts: prev.reconnectAttempts + 1,
      metrics: { ...prev.metrics, reconnectCount: prev.metrics.reconnectCount + 1 }
    }));

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Reconnecting... (attempt ${clientState.reconnectAttempts + 1}/${fullConfig.maxReconnectAttempts})`);
      // Connect will be called here - avoid circular dependency
      if (socketRef.current) {
        socketRef.current.connect();
      }
    }, fullConfig.reconnectInterval);
  }, [clientState.reconnectAttempts, fullConfig.maxReconnectAttempts, fullConfig.reconnectInterval, updateConnectionState]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    updateConnectionState(WebSocketConnectionState.CONNECTING);
    connectionStartTimeRef.current = Date.now();

    try {
      // Create socket connection with path matching backend
      socketRef.current = io(`${fullConfig.url}/ws/chat/${fullConfig.user_id}`, {
        transports: ['websocket', 'polling'],
        timeout: fullConfig.connectionTimeout,
        autoConnect: true
      });

      // Connection event handlers
      socketRef.current.on('connect', () => {
        console.log('WebSocket connected');
        updateConnectionState(WebSocketConnectionState.CONNECTED);
        setClientState(prev => ({ 
          ...prev, 
          reconnectAttempts: 0,
          metrics: {
            ...prev.metrics,
            connectionUptime: connectionStartTimeRef.current ? Date.now() - connectionStartTimeRef.current : 0
          }
        }));
        startPingInterval();
      });

      socketRef.current.on('disconnect', () => {
        console.log('WebSocket disconnected');
        updateConnectionState(WebSocketConnectionState.DISCONNECTED);
        stopPingInterval();
      });

      socketRef.current.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        updateConnectionState(WebSocketConnectionState.ERROR);
        handleReconnect();
      });

      // Message handler
      socketRef.current.on('message', handleMessage);

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      updateConnectionState(WebSocketConnectionState.ERROR);
      handleReconnect();
    }
  }, [fullConfig.url, fullConfig.user_id, fullConfig.connectionTimeout, updateConnectionState, handleMessage, startPingInterval, stopPingInterval, handleReconnect]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopPingInterval();

    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    updateConnectionState(WebSocketConnectionState.DISCONNECTED);
    setClientState(prev => ({ ...prev, reconnectAttempts: 0 }));
  }, [stopPingInterval, updateConnectionState]);

  // Reconnect manually
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 1000);
  }, [disconnect, connect]);

  // Send query
  const sendQuery = useCallback((query: string, sessionId?: string, databaseContext?: { database_name: string; session_id: string; [key: string]: unknown }): string => {
    const queryId = generateQueryId();
    
    // Create query state
    const queryState: QueryState = {
      query_id: queryId,
      query_text: query,
      status: QueryProgressStatus.QUEUED,
      progress: 0,
      start_time: Date.now()
    };

    // Add to active queries
    setActiveQueries(prev => new Map(prev.set(queryId, queryState)));

    // Send query message
    const queryMessage: QueryMessage = {
      type: WebSocketMessageType.QUERY,
      message: query,
      query_id: queryId,
      session_id: sessionId,
      database_context: databaseContext,
      timestamp: new Date().toISOString()
    };

    sendMessage(queryMessage);
    
    return queryId;
  }, [generateQueryId, sendMessage]);

  // Cancel query
  const cancelQuery = useCallback((queryId: string) => {
    setActiveQueries(prev => {
      const updated = new Map(prev);
      updated.delete(queryId);
      return updated;
    });
  }, []);

  // Request metrics
  const requestMetrics = useCallback(() => {
    sendMessage({
      type: WebSocketMessageType.METRICS,
      timestamp: new Date().toISOString()
    });
  }, [sendMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  return {
    connectionState,
    isConnected: clientState.isConnected,
    metrics: clientState.metrics,
    latency: clientState.latency,
    activeQueries,
    sendQuery,
    cancelQuery,
    connect,
    disconnect,
    reconnect,
    sendMessage,
    requestMetrics
  };
}
