/**
 * Global WebSocket Context
 * Provides global WebSocket connection state management
 */
"use client";

import React, { createContext, useContext, useRef, useState, useCallback } from 'react';
import { WebSocketConnectionState } from '@/types/websocket';
import { websocketManager } from '@/utils/websocket-manager';

interface WebSocketContextState {
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  connectionId: string | null;
  lastConnectedAt: number | null;
  connectionCount: number;
}

interface WebSocketContextValue extends WebSocketContextState {
  connect: (userId: string) => Promise<void>;
  disconnect: () => void;
  getConnection: () => WebSocket | null;
  resetConnectionCount: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [state, setState] = useState<WebSocketContextState>({
    connectionState: WebSocketConnectionState.DISCONNECTED,
    isConnected: false,
    connectionId: null,
    lastConnectedAt: null,
    connectionCount: 0
  });

  const isConnectingRef = useRef(false);
  const activeSocketRef = useRef<WebSocket | null>(null);
  const autoConnectAttemptedRef = useRef(false);

  const connect = useCallback(async (userId: string) => {
    if (isConnectingRef.current) {
      console.log('WebSocketContext: Connection already in progress');
      return;
    }

    if (state.isConnected && activeSocketRef.current) {
      console.log('WebSocketContext: Already connected');
      return;
    }

    try {
      isConnectingRef.current = true;
      const connectionId = `ctx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      setState(prev => ({
        ...prev,
        connectionState: WebSocketConnectionState.CONNECTING,
        connectionId,
        connectionCount: prev.connectionCount + 1
      }));

      const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';
      const wsUrl = `${wsBaseUrl}/ws/query/${userId}`;
      console.log(`WebSocketContext: Connecting to ${wsUrl} (ID: ${connectionId})`);
      console.log(`WebSocketContext: Environment NEXT_PUBLIC_WS_URL:`, process.env.NEXT_PUBLIC_WS_URL);
      console.log(`WebSocketContext: Final WebSocket URL:`, wsUrl);

      const socket = await websocketManager.getConnection(wsUrl);
      
      if (!socket) {
        console.log('WebSocketContext: Failed to get connection');
        setState(prev => ({
          ...prev,
          connectionState: WebSocketConnectionState.ERROR
        }));
        return;
      }

      activeSocketRef.current = socket;

      // Check if socket is already open (from manager's connection)
      if (socket.readyState === WebSocket.OPEN) {
        console.log(`WebSocketContext: Socket already open (ID: ${connectionId})`);
        console.log(`WebSocketContext: Setting state to CONNECTED`);
        setState(prev => {
          console.log(`WebSocketContext: Previous state:`, prev);
          const newState = {
            ...prev,
            connectionState: WebSocketConnectionState.CONNECTED,
            isConnected: true,
            lastConnectedAt: Date.now()
          };
          console.log(`WebSocketContext: New state:`, newState);
          return newState;
        });
        isConnectingRef.current = false;
      }

      socket.onopen = () => {
        console.log(`WebSocketContext: Connected (ID: ${connectionId})`);
        console.log(`WebSocketContext: Setting state to CONNECTED`);
        setState(prev => {
          console.log(`WebSocketContext: Previous state:`, prev);
          const newState = {
            ...prev,
            connectionState: WebSocketConnectionState.CONNECTED,
            isConnected: true,
            lastConnectedAt: Date.now()
          };
          console.log(`WebSocketContext: New state:`, newState);
          return newState;
        });
        isConnectingRef.current = false;
      };

      socket.onclose = () => {
        console.log(`WebSocketContext: Disconnected (ID: ${connectionId})`);
        setState(prev => ({
          ...prev,
          connectionState: WebSocketConnectionState.DISCONNECTED,
          isConnected: false
        }));
        activeSocketRef.current = null;
        isConnectingRef.current = false;
      };

      socket.onerror = (error) => {
        console.error(`WebSocketContext: Error (ID: ${connectionId}):`, error);
        setState(prev => ({
          ...prev,
          connectionState: WebSocketConnectionState.ERROR,
          isConnected: false
        }));
        activeSocketRef.current = null;
        isConnectingRef.current = false;
      };

    } catch (error) {
      console.error('WebSocketContext: Connection failed:', error);
      setState(prev => ({
        ...prev,
        connectionState: WebSocketConnectionState.ERROR
      }));
      isConnectingRef.current = false;
    }
  }, [state.isConnected]);

  const disconnect = useCallback(() => {
    console.log('WebSocketContext: Disconnect requested');
    console.trace('WebSocketContext: Disconnect call stack'); // Add stack trace to see what's calling disconnect
    isConnectingRef.current = false;
    
    if (activeSocketRef.current) {
      activeSocketRef.current.close();
      activeSocketRef.current = null;
    }
    
    websocketManager.closeConnection();
    
    setState(prev => ({
      ...prev,
      connectionState: WebSocketConnectionState.DISCONNECTED,
      isConnected: false
    }));
  }, []);

  const getConnection = useCallback(() => {
    return activeSocketRef.current;
  }, []);

  const resetConnectionCount = useCallback(() => {
    setState(prev => ({
      ...prev,
      connectionCount: 0
    }));
  }, []);

  // Auto-connect WebSocket on component mount (page load)
  React.useEffect(() => {
    if (!autoConnectAttemptedRef.current && !state.isConnected && !isConnectingRef.current) {
      autoConnectAttemptedRef.current = true;
      
      // Generate a default user ID for the session
      // Always generate a new session ID on page load to avoid conflicts
      const defaultUserId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Store the new user ID (this will replace any existing one)
      sessionStorage.setItem('websocket_user_id', defaultUserId);
      
      // Also store a session timestamp to help with debugging
      sessionStorage.setItem('websocket_session_started', Date.now().toString());
      
      console.log('WebSocketContext: Auto-connecting on page load with user ID:', defaultUserId);
      
      // Auto-connect after a short delay to ensure everything is initialized
      const connectTimeout = setTimeout(() => {
        connect(defaultUserId);
      }, 1000);

      // Cleanup function to handle page unload/reload
      const handleBeforeUnload = () => {
        console.log('WebSocketContext: Page unloading, cleaning up connection');
        disconnect();
      };

      // Add event listeners
      window.addEventListener('beforeunload', handleBeforeUnload);

      // Cleanup function - don't disconnect in development mode re-renders
      return () => {
        clearTimeout(connectTimeout);
        window.removeEventListener('beforeunload', handleBeforeUnload);
        // Don't disconnect on cleanup - let the WebSocket stay connected
        // The connection will be properly cleaned up on page unload via beforeunload
        console.log('WebSocketContext: Effect cleanup - preserving connection');
      };
    }
  }, [connect, disconnect]); // eslint-disable-line react-hooks/exhaustive-deps
  // Note: Intentionally excluding state.isConnected to prevent re-running when connection state changes

  // Separate effect for visibility change handling - only when connected
  React.useEffect(() => {
    if (!state.isConnected) return;

    let disconnectTimeout: NodeJS.Timeout | null = null;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        console.log('WebSocketContext: Page hidden, scheduling disconnect in 30 seconds...');
        // Delay disconnect for BI systems where users might switch tabs during long operations
        disconnectTimeout = setTimeout(() => {
          console.log('WebSocketContext: Page hidden timeout reached, cleaning up connection');
          disconnect();
        }, 30000); // 30 second delay
      } else if (document.visibilityState === 'visible') {
        // Cancel pending disconnect if page becomes visible again
        if (disconnectTimeout) {
          console.log('WebSocketContext: Page visible, cancelling scheduled disconnect');
          clearTimeout(disconnectTimeout);
          disconnectTimeout = null;
        }
        
        // Reconnect if disconnected
        if (!state.isConnected) {
          console.log('WebSocketContext: Page visible, reconnecting...');
          // Reset auto-connect flag to allow reconnection
          autoConnectAttemptedRef.current = false;
          setTimeout(() => {
            if (!state.isConnected && !isConnectingRef.current) {
              const userId = sessionStorage.getItem('websocket_user_id') || 
                             `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
              connect(userId);
            }
          }, 500);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      // Clear any pending disconnect timeout
      if (disconnectTimeout) {
        clearTimeout(disconnectTimeout);
      }
    };
  }, [state.isConnected, connect, disconnect]);

  const contextValue: WebSocketContextValue = {
    ...state,
    connect,
    disconnect,
    getConnection,
    resetConnectionCount
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useGlobalWebSocket(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useGlobalWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
