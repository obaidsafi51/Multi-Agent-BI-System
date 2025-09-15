/**
 * Global WebSocket Connection Manager
 * Ensures only one WebSocket connection exists at a time
 */

class WebSocketManager {
  private activeConnection: WebSocket | null = null;
  private connectionUrl: string | null = null;
  private isConnecting: boolean = false;

  public async getConnection(url: string): Promise<WebSocket | null> {
    // If we already have an active connection to the same URL, return it
    if (this.activeConnection && 
        this.connectionUrl === url && 
        this.activeConnection.readyState === WebSocket.OPEN) {
      console.log('WebSocketManager: Reusing existing connection');
      return this.activeConnection;
    }

    // If we're already connecting, wait
    if (this.isConnecting) {
      console.log('WebSocketManager: Connection in progress, waiting...');
      return null;
    }

    // Close any existing connection
    if (this.activeConnection) {
      console.log('WebSocketManager: Closing existing connection');
      this.activeConnection.close();
      this.activeConnection = null;
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
      this.activeConnection.close();
      this.activeConnection = null;
      this.connectionUrl = null;
    }
    this.isConnecting = false;
  }

  public getActiveConnection(): WebSocket | null {
    return this.activeConnection;
  }
}

// Export singleton instance
export const websocketManager = new WebSocketManager();
