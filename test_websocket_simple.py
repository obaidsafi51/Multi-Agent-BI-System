#!/usr/bin/env python3
"""
Simple test to check if NLP agent WebSocket endpoint exists
"""

import asyncio
import sys
import os

# Add the nlp-agent src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents', 'nlp-agent', 'src'))

from fastapi.testclient import TestClient

def test_websocket_endpoint():
    """Test that WebSocket endpoint is properly defined"""
    try:
        # Import the main app
        from agents.nlp_agent.main_optimized import app
        
        # Create test client
        client = TestClient(app)
        
        # Test basic HTTP endpoints first
        health_response = client.get("/health")
        print(f"Health endpoint status: {health_response.status_code}")
        
        # Test WebSocket endpoint exists
        with client.websocket_connect("/ws") as websocket:
            print("✅ WebSocket endpoint /ws is accessible")
            
            # Try to receive connection acknowledgment
            data = websocket.receive_json()
            print(f"📥 Connection ack: {data}")
            
            # Send test message
            test_msg = {"type": "heartbeat", "correlation_id": "test_001"}
            websocket.send_json(test_msg)
            
            # Receive response
            response = websocket.receive_json()
            print(f"📥 Heartbeat response: {response}")
            
            print("✅ Basic WebSocket communication working!")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the right directory and dependencies are installed")
    except Exception as e:
        print(f"❌ Test error: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    print("🧪 NLP Agent WebSocket Endpoint Test")
    print("=" * 40)
    test_websocket_endpoint()
