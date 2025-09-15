/**
 * WebSocket Connection Control Component
 * Provides manual controls for WebSocket connection management
 */
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Wifi, 
  WifiOff, 
  RotateCcw, 
  AlertCircle, 
  CheckCircle2,
  Clock,
  Zap
} from "lucide-react";
import { WebSocketConnectionState } from "@/types/websocket";

interface WebSocketConnectionControlProps {
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onReconnect: () => void;
  disabled?: boolean;
  compact?: boolean;
}

export function WebSocketConnectionControl({
  connectionState,
  isConnected,
  onConnect,
  onDisconnect,
  onReconnect,
  disabled = false,
  compact = false
}: WebSocketConnectionControlProps) {
  const [isManuallyDisconnected, setIsManuallyDisconnected] = useState(false);

  const getConnectionIcon = () => {
    switch (connectionState) {
      case WebSocketConnectionState.CONNECTED:
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case WebSocketConnectionState.CONNECTING:
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case WebSocketConnectionState.DISCONNECTED:
        return <WifiOff className="w-4 h-4 text-gray-500" />;
      case WebSocketConnectionState.ERROR:
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <WifiOff className="w-4 h-4 text-gray-500" />;
    }
  };

  const getConnectionStatus = () => {
    switch (connectionState) {
      case WebSocketConnectionState.CONNECTED:
        return { text: "Connected", variant: "default" as const };
      case WebSocketConnectionState.CONNECTING:
        return { text: "Connecting", variant: "secondary" as const };
      case WebSocketConnectionState.DISCONNECTED:
        return { text: "Disconnected", variant: "outline" as const };
      case WebSocketConnectionState.ERROR:
        return { text: "Error", variant: "destructive" as const };
      default:
        return { text: "Unknown", variant: "outline" as const };
    }
  };

  const handleConnect = () => {
    setIsManuallyDisconnected(false);
    onConnect();
  };

  const handleDisconnect = () => {
    setIsManuallyDisconnected(true);
    onDisconnect();
  };

  const handleReconnect = () => {
    setIsManuallyDisconnected(false);
    onReconnect();
  };

  const status = getConnectionStatus();

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          {getConnectionIcon()}
          <Badge variant={status.variant} className="text-xs">
            {status.text}
          </Badge>
        </div>

        {!isConnected ? (
          <Button
            size="sm"
            variant="outline"
            onClick={handleConnect}
            disabled={disabled || connectionState === WebSocketConnectionState.CONNECTING}
            className="h-6 px-2"
            title="Connect WebSocket"
          >
            <Wifi className="w-3 h-3" />
          </Button>
        ) : (
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="outline"
              onClick={handleDisconnect}
              disabled={disabled}
              className="h-6 px-2"
              title="Disconnect WebSocket"
            >
              <WifiOff className="w-3 h-3" />
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={handleReconnect}
              disabled={disabled}
              className="h-6 px-2"
              title="Reconnect WebSocket"
            >
              <RotateCcw className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Zap className="w-4 h-4" />
          WebSocket Connection
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getConnectionIcon()}
            <Badge variant={status.variant}>
              {status.text}
            </Badge>
          </div>
        </div>

        <div className="flex gap-2">
          {!isConnected ? (
            <Button
              size="sm"
              onClick={handleConnect}
              disabled={disabled || connectionState === WebSocketConnectionState.CONNECTING}
              className="flex-1"
            >
              <Wifi className="w-4 h-4 mr-2" />
              Connect
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleDisconnect}
                disabled={disabled}
                className="flex-1"
              >
                <WifiOff className="w-4 h-4 mr-2" />
                Disconnect
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleReconnect}
                disabled={disabled}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </>
          )}
        </div>

        {isManuallyDisconnected && (
          <div className="text-xs text-muted-foreground">
            Manually disconnected. Click Connect to reconnect.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
