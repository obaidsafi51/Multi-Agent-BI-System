#!/usr/bin/env python3
"""
NLP Agent Startup Script

Starts both HTTP API server and WebSocket server concurrently.
This ensures the NLP agent can handle both traditional HTTP requests 
and real-time WebSocket connections from the backend.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import List

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)


class NLPAgentLauncher:
    """Manages startup and shutdown of both HTTP and WebSocket servers"""
    
    def __init__(self):
        self.tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
        # Configuration from environment
        self.http_host = os.getenv("HOST", "0.0.0.0")
        self.http_port = int(os.getenv("PORT", "8001"))
        # Disable standalone WebSocket server - NLP agent connects as client to MCP server
        self.websocket_enabled = False  # os.getenv("ENABLE_WEBSOCKETS", "true").lower() == "true"
        self.websocket_host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        self.websocket_port = int(os.getenv("WEBSOCKET_PORT", "8011"))
        
        logger.info(f"NLP Agent Configuration:")
        logger.info(f"  HTTP Server: {self.http_host}:{self.http_port}")
        logger.info(f"  WebSocket Enabled: {self.websocket_enabled}")
        if self.websocket_enabled:
            logger.info(f"  WebSocket Server: {self.websocket_host}:{self.websocket_port}")
    
    async def start_http_server(self):
        """Start the HTTP API server"""
        try:
            logger.info("Starting HTTP API server...")
            # Import here to avoid circular imports
            from main import app
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=self.http_host,
                port=self.http_port,
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"HTTP server failed: {e}")
            raise
    
    async def start_websocket_server(self):
        """WebSocket server disabled - NLP agent acts as client only"""
        logger.info("WebSocket server disabled - NLP agent connects as client to MCP server")
        return
    
    async def run(self):
        """Run both servers concurrently"""
        try:
            logger.info("Starting NLP Agent with HTTP and WebSocket servers...")
            
            # Create tasks for both servers
            http_task = asyncio.create_task(
                self.start_http_server(),
                name="http-server"
            )
            self.tasks.append(http_task)
            
            if self.websocket_enabled:
                websocket_task = asyncio.create_task(
                    self.start_websocket_server(),
                    name="websocket-server"
                )
                self.tasks.append(websocket_task)
            
            # Set up signal handlers for graceful shutdown
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(sig, self.signal_handler)
            
            # Wait for either server to fail or shutdown signal
            done, pending = await asyncio.wait(
                self.tasks + [asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If shutdown was triggered, clean up
            if self.shutdown_event.is_set():
                logger.info("Shutdown signal received")
            else:
                # One of the servers failed
                for task in done:
                    if task.get_name() in ["http-server", "websocket-server"]:
                        try:
                            await task  # Re-raise the exception
                        except Exception as e:
                            logger.error(f"Server task {task.get_name()} failed: {e}")
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            logger.error(f"NLP Agent startup failed: {e}")
            raise
        finally:
            logger.info("NLP Agent shutdown complete")
    
    def signal_handler(self):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        self.shutdown_event.set()


async def main():
    """Main entry point"""
    launcher = NLPAgentLauncher()
    try:
        await launcher.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle case where asyncio.run is called in an already running loop
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # We're in a Jupyter notebook or similar environment
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise
