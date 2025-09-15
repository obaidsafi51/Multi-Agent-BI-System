/**
 * Simplified WebSocket Client Hook
 * Basic implementation to connect to FastAPI WebSocket endpoint
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  WebSocketConnectionState,
  UseWebSocketReturn,
  WebSocketMessage
} from '@/types/websocket';
import { websocketManager } from '@/utils/websocket-manager';

interface SimpleWebSocketConfig {
  url?: string;
  user_id?: string;
  reconnect?: boolean;
  maxReconnectAttempts?: number;
}

const DEFAULT_CONFIG: SimpleWebSocketConfig = {
  url: process.env.NEXT_PUBLIC_BACKEND_URL || 'ws://localhost:8080',
  user_id: 'default_user',
  reconnect: false,  // Disable auto-reconnect to prevent storm
  maxReconnectAttempts: 0
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

  // Refs for connection state management and React Strict Mode protection
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const isConnectingRef = useRef(false); // Prevent multiple connection attempts
  const hasConnectedRef = useRef(false); // Track if we've ever connected
  const connectionIdRef = useRef<string | null>(null); // Unique connection ID
  const strictModeCounterRef = useRef(0); // Track React Strict Mode double renders

  // Connect to WebSocket with React Strict Mode protection
  const connect = useCallback(async () => {
    // React Strict Mode protection: Track render attempts
    strictModeCounterRef.current += 1;
    const currentAttempt = strictModeCounterRef.current;
    
    // Generate unique connection ID for this attempt
    const connectionId = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    connectionIdRef.current = connectionId;
    
    console.log(`useWebSocketClient: Connect attempt #${currentAttempt} (ID: ${connectionId})`);
    
    // Prevent multiple connection attempts
    if (isConnectingRef.current) {
      console.log('useWebSocketClient: Connection already in progress, skipping');
      return;
    }
    
    // Use global connection manager to prevent multiple connections
    const wsUrl = `ws://localhost:8080/ws/chat/${fullConfig.user_id}`;
    
    try {
      isConnectingRef.current = true;
      setConnectionState(WebSocketConnectionState.CONNECTING);
      console.log(`useWebSocketClient: Requesting connection to: ${wsUrl} (ID: ${connectionId})`);
      
      const socket = await websocketManager.getConnection(wsUrl);
      
      if (!socket) {
        console.log('useWebSocketClient: Connection not available (likely in progress)');
        isConnectingRef.current = false;
        return;
      }

      // Verify this is still the latest connection attempt
      if (connectionIdRef.current !== connectionId) {
        console.log(`useWebSocketClient: Connection attempt ${connectionId} superseded, aborting`);
        isConnectingRef.current = false;
        return;
      }

      socketRef.current = socket;

      // If already connected, update state immediately
      if (socket.readyState === WebSocket.OPEN) {
        console.log('useWebSocketClient: Using existing connection');
        setConnectionState(WebSocketConnectionState.CONNECTED);
        setIsConnected(true);
        return;
      }

      // Set up event handlers for new connection
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('Received WebSocket message:', message);
          // Handle message based on type
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      socket.onopen = () => {
        console.log('useWebSocketClient: Connection established');
        setConnectionState(WebSocketConnectionState.CONNECTED);
        setIsConnected(true);
        reconnectAttempts.current = 0;
        hasConnectedRef.current = true;
        isConnectingRef.current = false;
      };

      socket.onclose = (event) => {
        console.log('useWebSocketClient: Connection closed:', event.code, event.reason);
        setConnectionState(WebSocketConnectionState.DISCONNECTED);
        setIsConnected(false);
        isConnectingRef.current = false;
        socketRef.current = null;
        
        // Only attempt reconnect if we were previously connected and reconnect is enabled
        if (hasConnectedRef.current && fullConfig.reconnect && 
            reconnectAttempts.current < (fullConfig.maxReconnectAttempts || 0)) {
          reconnectAttempts.current++;
          setTimeout(connect, 1000 * Math.pow(2, reconnectAttempts.current));
        }
      };

      socket.onerror = (error) => {
        console.error('useWebSocketClient: Connection error:', error);
        setConnectionState(WebSocketConnectionState.ERROR);
        isConnectingRef.current = false;
      };

    } catch (error) {
      console.error(`useWebSocketClient: Failed to get connection (ID: ${connectionId}):`, error);
      setConnectionState(WebSocketConnectionState.ERROR);
      isConnectingRef.current = false;
    }
  }, [fullConfig]);

  // Disconnect
  const disconnect = useCallback(() => {
    console.log('useWebSocketClient: Disconnect called');
    isConnectingRef.current = false;
    hasConnectedRef.current = false;
    
    // Use global connection manager for proper cleanup
    websocketManager.closeConnection();
    socketRef.current = null;
    
    setConnectionState(WebSocketConnectionState.DISCONNECTED);
    setIsConnected(false);
  }, []);

  // Send query
  const sendQuery = useCallback((query: string, sessionId?: string, databaseContext?: Record<string, unknown>): string => {
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
  const sendMessage = useCallback((message: WebSocketMessage) => {
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
      console.log('useWebSocketClient cleanup');
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
