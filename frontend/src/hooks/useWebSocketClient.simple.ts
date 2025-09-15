/**
 * Simplified WebSocket Client Hook
 * Basic implementation to connect to FastAPI WebSocket endpoint
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  WebSocketConnectionState,
  WebSocketMessageType,
  QueryProgressStatus,
  UseWebSocketReturn,
  WebSocketClientState
} from '@/types/websocket';

interface SimpleWebSocketConfig {
  url?: string;
  user_id?: string;
  reconnect?: boolean;
  maxReconnectAttempts?: number;
}

const DEFAULT_CONFIG: SimpleWebSocketConfig = {
  url: process.env.NEXT_PUBLIC_BACKEND_URL || 'ws://localhost:8000',
  user_id: 'default_user',
  reconnect: true,
  maxReconnectAttempts: 5
};

export function useWebSocketClient(config?: SimpleWebSocketConfig): UseWebSocketReturn {
  const fullConfig = useMemo(() => ({ ...DEFAULT_CONFIG, ...config }), [config]);

  // State
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>(
    WebSocketConnectionState.DISCONNECTED
  );
  const [isConnected, setIsConnected] = useState(false);
  const [activeQueries] = useState(new Map());
  const [metrics] = useState({
    messagesReceived: 0,
    messagesSent: 0,
    reconnectCount: 0,
    connectionUptime: 0
  });

  // Refs
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.CONNECTING || 
        socketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = fullConfig.url!.replace(/^http/, 'ws');
    const fullUrl = `${wsUrl}/ws/chat/${fullConfig.user_id}`;
    
    console.log('Connecting to WebSocket:', fullUrl);
    setConnectionState(WebSocketConnectionState.CONNECTING);

    try {
      socketRef.current = new WebSocket(fullUrl);

      socketRef.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setConnectionState(WebSocketConnectionState.CONNECTED);
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      socketRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionState(WebSocketConnectionState.DISCONNECTED);
        setIsConnected(false);
        
        // Auto-reconnect if enabled
        if (fullConfig.reconnect && reconnectAttempts.current < fullConfig.maxReconnectAttempts!) {
          reconnectAttempts.current++;
          setTimeout(() => {
            connect();
          }, 1000 * reconnectAttempts.current);
        }
      };

      socketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState(WebSocketConnectionState.ERROR);
      };

      socketRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('WebSocket message received:', message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState(WebSocketConnectionState.ERROR);
    }
  }, [fullConfig]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setConnectionState(WebSocketConnectionState.DISCONNECTED);
    setIsConnected(false);
  }, []);

  // Send query
  const sendQuery = useCallback((query: string, sessionId?: string, databaseContext?: any): string => {
    if (!isConnected || !socketRef.current) {
      console.warn('WebSocket not connected, cannot send query');
      return '';
    }

    const queryId = `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const message = {
      type: 'query',
      message: query,
      query_id: queryId,
      session_id: sessionId,
      database_context: databaseContext
    };

    try {
      socketRef.current.send(JSON.stringify(message));
      console.log('Query sent:', message);
      return queryId;
    } catch (error) {
      console.error('Failed to send query:', error);
      return '';
    }
  }, [isConnected]);

  // Send message
  const sendMessage = useCallback((message: any) => {
    if (!isConnected || !socketRef.current) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }

    try {
      socketRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // Connection state
    connectionState,
    isConnected,
    metrics,
    latency: null,
    
    // Query management
    activeQueries,
    sendQuery,
    cancelQuery: () => {},
    
    // Connection management
    connect,
    disconnect,
    reconnect: connect,
    
    // Utilities
    sendMessage,
    requestMetrics: () => {}
  };
}
