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
  disableCleanup?: boolean;
}

// Helper function to get WebSocket URL from environment
const getWebSocketUrl = (): string => {
  // Try WebSocket-specific URL first
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  
  // Convert HTTP backend URL to WebSocket URL
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  }
  
  // Convert API URL to WebSocket URL
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  }
  
  // Development fallback - only used if no environment variables are set
  console.warn('⚠️  No WebSocket environment variables found, using development fallback');
  return process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';
};

const DEFAULT_CONFIG: SimpleWebSocketConfig = {
  url: getWebSocketUrl(),
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
    
    // Generate stable agent ID using user_id and browser session (consistent with backend)
    const sessionId = sessionStorage.getItem('websocket_session_id') || 
                     `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    if (!sessionStorage.getItem('websocket_session_id')) {
      sessionStorage.setItem('websocket_session_id', sessionId);
    }
    const connectionId = `frontend_${fullConfig.user_id}_${sessionId}`;
    connectionIdRef.current = connectionId;
    
    console.log(`useWebSocketClient: Connect attempt #${currentAttempt} (ID: ${connectionId})`);
    
    // Prevent multiple connection attempts
    if (isConnectingRef.current) {
      console.log('useWebSocketClient: Connection already in progress, skipping');
      return;
    }
    
    // Use global connection manager to prevent multiple connections
    let baseUrl = fullConfig.url;
    
    // Ensure we have a WebSocket URL
    if (!baseUrl) {
      console.error('❌ No WebSocket URL configured - check environment variables');
      throw new Error('WebSocket URL not configured');
    }
    
    // Convert HTTP to WebSocket protocol if needed
    if (baseUrl.startsWith('http://')) {
      baseUrl = baseUrl.replace('http://', 'ws://');
    } else if (baseUrl.startsWith('https://')) {
      baseUrl = baseUrl.replace('https://', 'wss://');
    }
    
    const wsUrl = `${baseUrl}/ws/chat/${fullConfig.user_id}`;
    
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
          
          // Handle standardized message types
          switch (message.type) {
            case 'connection_acknowledged':
              console.log('Connection handshake acknowledged:', message.server_agent_id);
              console.log('Server capabilities:', message.server_capabilities);
              break;
            case 'heartbeat_response':
              console.log('Heartbeat acknowledged:', message.server_status);
              break;
            case 'connection_established':
              console.log('Connection established:', message.message);
              break;
            case 'query_response':
              console.log('Query response received:', message.response);
              break;
            case 'query_processing_started':
              console.log('Query processing started:', message.query);
              break;
            case 'error':
              console.error('Server error:', message.error);
              break;
            default:
              console.log('Unhandled message type:', message.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      socket.onopen = () => {
        console.log('useWebSocketClient: Connection established, sending handshake');
        
        // Send connection handshake with agent information
        const handshakeMessage = {
          type: 'connection_handshake',
          agent_id: connectionId,
          agent_type: 'frontend',
          user_id: fullConfig.user_id,
          capabilities: ['query_processing', 'real_time_updates', 'heartbeat'],
          timestamp: new Date().toISOString(),
          client_info: {
            browser: navigator.userAgent,
            url: window.location.href
          }
        };
        
        try {
          socket.send(JSON.stringify(handshakeMessage));
          console.log('Handshake sent:', handshakeMessage);
        } catch (error) {
          console.error('Failed to send handshake:', error);
        }
        
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

  // Send query with standardized format
  const sendQuery = useCallback((query: string, sessionId?: string, databaseContext?: Record<string, unknown>): string => {
    if (!isConnected || !socketRef.current) {
      console.warn('WebSocket not connected, cannot send query');
      return '';
    }

    const queryId = `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Standardized message format compatible with backend
    const message = {
      type: 'query',
      query: query,  // Use 'query' instead of 'message' for consistency
      query_id: queryId,
      session_id: sessionId || `frontend_session_${Date.now()}`,
      database_context: databaseContext || {},
      preferences: { output_format: 'json' },
      timestamp: new Date().toISOString(),
      correlation_id: queryId
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

  // Cleanup on unmount (only if cleanup is not disabled)
  useEffect(() => {
    if (config?.disableCleanup) {
      console.log('useWebSocketClient cleanup disabled');
      return;
    }
    
    return () => {
      console.log('useWebSocketClient cleanup');
      disconnect();
    };
  }, [disconnect, config?.disableCleanup]);

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
