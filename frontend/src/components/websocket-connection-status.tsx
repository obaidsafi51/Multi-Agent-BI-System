/**
 * WebSocket Connection Status Indicator
 * Shows real-time connection state, latency, and health metrics
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog';
import { 
  Wifi, 
  WifiOff, 
  Loader2, 
  AlertTriangle, 
  Zap, 
  Activity,
  Info
} from 'lucide-react';
import {
  WebSocketConnectionState,
  WebSocketConnectionStatusProps
} from '@/types/websocket';

export function WebSocketConnectionStatus({
  connectionState,
  latency = null,
  showDetails = false,
  size = 'md'
}: WebSocketConnectionStatusProps) {

  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  // Get connection display information
  const getConnectionDisplay = (state: WebSocketConnectionState) => {
    switch (state) {
      case WebSocketConnectionState.CONNECTED:
        return {
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          badgeVariant: 'default' as const,
          badgeClass: 'bg-green-100 text-green-800 border-green-200',
          icon: <Wifi className={`${getSizeClass(size)} text-green-600`} />,
          label: 'Connected',
          description: 'Real-time connection active',
          pulseColor: 'bg-green-500'
        };
      case WebSocketConnectionState.CONNECTING:
        return {
          color: 'text-blue-600',
          bgColor: 'bg-blue-100',
          badgeVariant: 'secondary' as const,
          badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
          icon: <Loader2 className={`${getSizeClass(size)} text-blue-600 animate-spin`} />,
          label: 'Connecting',
          description: 'Establishing connection...',
          pulseColor: 'bg-blue-500'
        };
      case WebSocketConnectionState.RECONNECTING:
        return {
          color: 'text-orange-600',
          bgColor: 'bg-orange-100',
          badgeVariant: 'secondary' as const,
          badgeClass: 'bg-orange-100 text-orange-800 border-orange-200',
          icon: <Loader2 className={`${getSizeClass(size)} text-orange-600 animate-spin`} />,
          label: 'Reconnecting',
          description: 'Attempting to reconnect...',
          pulseColor: 'bg-orange-500'
        };
      case WebSocketConnectionState.ERROR:
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          badgeVariant: 'destructive' as const,
          badgeClass: 'bg-red-100 text-red-800 border-red-200',
          icon: <AlertTriangle className={`${getSizeClass(size)} text-red-600`} />,
          label: 'Error',
          description: 'Connection failed',
          pulseColor: 'bg-red-500'
        };
      case WebSocketConnectionState.DISCONNECTED:
      default:
        return {
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          badgeVariant: 'secondary' as const,
          badgeClass: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: <WifiOff className={`${getSizeClass(size)} text-gray-600`} />,
          label: 'Disconnected',
          description: 'No connection',
          pulseColor: 'bg-gray-500'
        };
    }
  };

  // Get size classes
  function getSizeClass(size: 'sm' | 'md' | 'lg') {
    switch (size) {
      case 'sm': return 'h-3 w-3';
      case 'lg': return 'h-6 w-6';
      case 'md':
      default: return 'h-4 w-4';
    }
  }

  // Get container size classes
  function getContainerSize(size: 'sm' | 'md' | 'lg') {
    switch (size) {
      case 'sm': return 'p-1';
      case 'lg': return 'p-3';
      case 'md':
      default: return 'p-2';
    }
  }

  // Format latency
  const formatLatency = (ms: number): string => {
    if (ms < 100) return `${ms}ms`;
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // Get latency color
  const getLatencyColor = (ms: number): string => {
    if (ms < 50) return 'text-green-600';
    if (ms < 100) return 'text-yellow-600';
    if (ms < 200) return 'text-orange-600';
    return 'text-red-600';
  };

  const display = getConnectionDisplay(connectionState);

  // Simple compact indicator
  if (size === 'sm' && !showDetails) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-1"
      >
        <div className={`relative ${getContainerSize(size)} rounded-full ${display.bgColor}`}>
          {display.icon}
          {connectionState === WebSocketConnectionState.CONNECTED && (
            <motion.div
              animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className={`absolute inset-0 rounded-full ${display.pulseColor} opacity-30`}
            />
          )}
        </div>
        <span className={`text-xs font-medium ${display.color}`}>
          {display.label}
        </span>
      </motion.div>
    );
  }

  // Standard indicator with optional details
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2"
    >
      {/* Connection Status Badge */}
      <Badge className={`flex items-center gap-1.5 ${display.badgeClass} font-medium`}>
        <div className="relative">
          {display.icon}
          {connectionState === WebSocketConnectionState.CONNECTED && (
            <motion.div
              animate={{ scale: [1, 1.2, 1], opacity: [0.8, 0.3, 0.8] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className={`absolute -inset-1 rounded-full ${display.pulseColor} opacity-30 blur-sm`}
            />
          )}
        </div>
        <span className="text-sm">{display.label}</span>
      </Badge>

      {/* Latency Display */}
      {latency !== null && connectionState === WebSocketConnectionState.CONNECTED && (
        <motion.div
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 'auto' }}
          className="flex items-center gap-1"
        >
          <Zap className="h-3 w-3 text-gray-500" />
          <span className={`text-xs font-medium ${getLatencyColor(latency)}`}>
            {formatLatency(latency)}
          </span>
        </motion.div>
      )}

      {/* Details Button */}
      {showDetails && (
        <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
          <DialogTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 rounded-full hover:bg-gray-100"
            >
              <Info className="h-3 w-3 text-gray-500" />
            </Button>
          </DialogTrigger>
          
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-600" />
                WebSocket Connection
              </DialogTitle>
              <DialogDescription>
                Real-time connection status and performance metrics
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Current Status */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Current Status</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${display.bgColor}`}>
                      {display.icon}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{display.label}</div>
                      <div className="text-sm text-gray-600">{display.description}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Performance Metrics */}
              {connectionState === WebSocketConnectionState.CONNECTED && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Performance</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 space-y-3">
                    {latency !== null && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Latency</span>
                        <span className={`text-sm font-medium ${getLatencyColor(latency)}`}>
                          {formatLatency(latency)}
                        </span>
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Protocol</span>
                      <span className="text-sm font-medium text-gray-900">WebSocket</span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Auto-reconnect</span>
                      <span className="text-sm font-medium text-green-600">Enabled</span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Connection Tips */}
              <Card className="bg-blue-50/50 border-blue-200">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-blue-900 font-medium mb-1">Connection Info</p>
                      <p className="text-xs text-blue-700 leading-relaxed">
                        {connectionState === WebSocketConnectionState.CONNECTED
                          ? "Real-time connection active. Query results will stream instantly."
                          : connectionState === WebSocketConnectionState.CONNECTING || connectionState === WebSocketConnectionState.RECONNECTING
                          ? "Establishing connection. Please wait a moment."
                          : "Connection unavailable. Queries will use HTTP fallback."
                        }
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </motion.div>
  );
}

// Simple status dot component for minimal displays
export function WebSocketStatusDot({ 
  connectionState, 
  size = 'sm' 
}: { 
  connectionState: WebSocketConnectionState; 
  size?: 'xs' | 'sm' | 'md' 
}) {
  const display = getConnectionDisplay(connectionState);
  
  const sizeClasses = {
    xs: 'w-2 h-2',
    sm: 'w-3 h-3', 
    md: 'w-4 h-4'
  };

  function getConnectionDisplay(state: WebSocketConnectionState) {
    switch (state) {
      case WebSocketConnectionState.CONNECTED:
        return { color: 'bg-green-500', pulseColor: 'bg-green-400' };
      case WebSocketConnectionState.CONNECTING:
      case WebSocketConnectionState.RECONNECTING:
        return { color: 'bg-blue-500', pulseColor: 'bg-blue-400' };
      case WebSocketConnectionState.ERROR:
        return { color: 'bg-red-500', pulseColor: 'bg-red-400' };
      default:
        return { color: 'bg-gray-400', pulseColor: 'bg-gray-300' };
    }
  }

  return (
    <div className="relative">
      <div className={`${sizeClasses[size]} rounded-full ${display.color}`} />
      {connectionState === WebSocketConnectionState.CONNECTED && (
        <motion.div
          animate={{ scale: [1, 2, 1], opacity: [0.8, 0, 0.8] }}
          transition={{ duration: 2, repeat: Infinity }}
          className={`absolute inset-0 ${sizeClasses[size]} rounded-full ${display.pulseColor} opacity-40`}
        />
      )}
    </div>
  );
}
