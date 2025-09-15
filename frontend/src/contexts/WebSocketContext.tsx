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

      const wsUrl = `ws://localhost:8080/ws/chat/${userId}`;
      console.log(`WebSocketContext: Connecting to ${wsUrl} (ID: ${connectionId})`);

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

      socket.onopen = () => {
        console.log(`WebSocketContext: Connected (ID: ${connectionId})`);
        setState(prev => ({
          ...prev,
          connectionState: WebSocketConnectionState.CONNECTED,
          isConnected: true,
          lastConnectedAt: Date.now()
        }));
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
