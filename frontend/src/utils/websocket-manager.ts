/**
 * Global WebSocket Connection Manager
 * Ensures only one WebSocket connection exists at a time
 */

class WebSocketManager {
  private activeConnection: WebSocket | null = null;
  private connectionUrl: string | null = null;
  private isConnecting: boolean = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  public async getConnection(url: string): Promise<WebSocket | null> {
    // If we already have an active connection to the same URL, return it
    if (this.activeConnection && 
        this.connectionUrl === url && 
        this.activeConnection.readyState === WebSocket.OPEN) {
      console.log('WebSocketManager: Reusing existing connection');
      return this.activeConnection;
    }

    // If we're already connecting, wait for a short period
    if (this.isConnecting) {
      console.log('WebSocketManager: Connection in progress, waiting...');
      // Wait for up to 3 seconds for the current connection attempt
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        if (!this.isConnecting) break;
      }
      
      // If still connecting, cancel this request
      if (this.isConnecting) {
        console.log('WebSocketManager: Connection timeout, cancelling');
        return null;
      }
      
      // If connection was established while waiting, return it
      if (this.activeConnection && this.activeConnection.readyState === WebSocket.OPEN) {
        return this.activeConnection;
      }
    }

    // Close any existing connection properly
    if (this.activeConnection) {
      console.log('WebSocketManager: Closing existing connection');
      this.activeConnection.close();
      this.activeConnection = null;
      this.connectionUrl = null;
      
      // Wait a bit for the connection to close properly
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
      this.isConnecting = true;
      console.log('WebSocketManager: Creating new connection to', url);
      
      const socket = new WebSocket(url);
      
      return new Promise((resolve, reject) => {
        socket.onopen = () => {
          console.log('WebSocketManager: Connection established');
          this.activeConnection = socket;
          this.connectionUrl = url;
          this.isConnecting = false;
          this.startHeartbeat();
          resolve(socket);
        };

        socket.onerror = (error) => {
          console.error('WebSocketManager: Connection error', error);
          this.isConnecting = false;
          reject(error);
        };

        socket.onclose = () => {
          console.log('WebSocketManager: Connection closed');
          if (this.activeConnection === socket) {
            this.stopHeartbeat();
            this.activeConnection = null;
            this.connectionUrl = null;
          }
          this.isConnecting = false;
        };
      });
    } catch (error) {
      this.isConnecting = false;
      console.error('WebSocketManager: Failed to create connection', error);
      return null;
    }
  }

  public closeConnection(): void {
    if (this.activeConnection) {
      console.log('WebSocketManager: Manually closing connection');
      this.stopHeartbeat();
      this.activeConnection.close();
      this.activeConnection = null;
      this.connectionUrl = null;
    }
    this.isConnecting = false;
  }

  public getActiveConnection(): WebSocket | null {
    return this.activeConnection;
  }

  private startHeartbeat(): void {
    // Clear any existing heartbeat
    this.stopHeartbeat();
    
    // Send heartbeat every 30 seconds
    this.heartbeatInterval = setInterval(() => {
      if (this.activeConnection && this.activeConnection.readyState === WebSocket.OPEN) {
        try {
          this.activeConnection.send(JSON.stringify({
            type: 'heartbeat',
            timestamp: new Date().toISOString()
          }));
        } catch (error) {
          console.error('WebSocketManager: Failed to send heartbeat', error);
        }
      } else {
        this.stopHeartbeat();
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

// Export singleton instance
export const websocketManager = new WebSocketManager();
