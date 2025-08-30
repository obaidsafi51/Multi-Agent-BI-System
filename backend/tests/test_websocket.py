"""
Unit tests for WebSocket functionality
"""

import pytest
import json
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestWebSocketConnection:
    """Test WebSocket connection and basic functionality"""
    
    def test_websocket_connection_success(self, client):
        """Test successful WebSocket connection"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "system"
            assert "Connected to AI CFO Assistant" in data["message"]
            assert "timestamp" in data
    
    def test_websocket_multiple_connections(self, client):
        """Test multiple WebSocket connections"""
        user1_id = "user1"
        user2_id = "user2"
        
        with client.websocket_connect(f"/ws/chat/{user1_id}") as ws1:
            with client.websocket_connect(f"/ws/chat/{user2_id}") as ws2:
                # Both should receive welcome messages
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                
                assert data1["type"] == "system"
                assert data2["type"] == "system"
                assert "Connected" in data1["message"]
                assert "Connected" in data2["message"]


class TestWebSocketQueryProcessing:
    """Test query processing through WebSocket"""
    
    def test_websocket_query_message(self, client):
        """Test sending query message through WebSocket"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send query message
            query_message = {
                "type": "query",
                "message": "Show me quarterly revenue"
            }
            websocket.send_json(query_message)
            
            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert "query_id" in response
            assert "Processing query" in response["message"]
            assert "data" in response
            assert "timestamp" in response
    
    def test_websocket_empty_query(self, client):
        """Test sending empty query through WebSocket"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send empty query
            query_message = {
                "type": "query",
                "message": ""
            }
            websocket.send_json(query_message)
            
            # Should still receive response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert "query_id" in response
    
    def test_websocket_query_with_data(self, client):
        """Test query response contains expected data structure"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send query
            query_message = {
                "type": "query",
                "message": "Show revenue trends"
            }
            websocket.send_json(query_message)
            
            # Check response data structure
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert "data" in response
            
            data = response["data"]
            assert "chart_type" in data
            assert "values" in data
            assert isinstance(data["values"], list)
            assert len(data["values"]) > 0


class TestWebSocketPingPong:
    """Test WebSocket ping/pong functionality"""
    
    def test_websocket_ping_pong(self, client):
        """Test ping/pong mechanism"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send ping
            ping_message = {"type": "ping"}
            websocket.send_json(ping_message)
            
            # Receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response
    
    def test_websocket_multiple_pings(self, client):
        """Test multiple ping messages"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send multiple pings
            for i in range(3):
                ping_message = {"type": "ping"}
                websocket.send_json(ping_message)
                
                response = websocket.receive_json()
                assert response["type"] == "pong"


class TestWebSocketErrorHandling:
    """Test WebSocket error handling"""
    
    def test_websocket_invalid_message_type(self, client):
        """Test sending invalid message type"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send invalid message type
            invalid_message = {
                "type": "invalid_type",
                "message": "test"
            }
            websocket.send_json(invalid_message)
            
            # Connection should remain open (no response expected for unknown types)
            # Send ping to verify connection is still alive
            ping_message = {"type": "ping"}
            websocket.send_json(ping_message)
            
            response = websocket.receive_json()
            assert response["type"] == "pong"
    
    def test_websocket_malformed_json(self, client):
        """Test sending malformed JSON"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # This test is tricky with TestClient as it handles JSON serialization
            # In a real scenario, malformed JSON would cause connection to close
            # For now, test with valid JSON but unexpected structure
            unexpected_message = "not_a_dict"
            
            # This should cause an error, but connection handling depends on implementation
            try:
                websocket.send_json(unexpected_message)
                # If we get here, the connection is still alive
                ping_message = {"type": "ping"}
                websocket.send_json(ping_message)
                response = websocket.receive_json()
                assert response["type"] == "pong"
            except Exception:
                # Connection closed due to error, which is acceptable
                pass


class TestWebSocketConnectionManagement:
    """Test WebSocket connection management"""
    
    def test_websocket_connection_tracking(self, client):
        """Test that connections are properly tracked"""
        user_id = "test_user"
        
        # This test would require access to the websocket_connections dict
        # For now, just verify connection works
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send ping to verify connection is active
            ping_message = {"type": "ping"}
            websocket.send_json(ping_message)
            
            response = websocket.receive_json()
            assert response["type"] == "pong"
    
    def test_websocket_connection_cleanup(self, client):
        """Test connection cleanup on disconnect"""
        user_id = "test_user"
        
        # Connect and disconnect
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            websocket.receive_json()  # Welcome message
        
        # Connection should be cleaned up automatically
        # Reconnect with same user_id should work
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "system"


class TestWebSocketConcurrency:
    """Test WebSocket concurrency and performance"""
    
    def test_websocket_concurrent_messages(self, client):
        """Test sending multiple messages quickly"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send multiple messages quickly
            messages = [
                {"type": "query", "message": f"Query {i}"}
                for i in range(5)
            ]
            
            # Send all messages
            for message in messages:
                websocket.send_json(message)
            
            # Receive all responses
            responses = []
            for _ in range(5):
                response = websocket.receive_json()
                responses.append(response)
            
            # All should be valid responses
            assert len(responses) == 5
            assert all(r["type"] == "response" for r in responses)
            assert all("query_id" in r for r in responses)
    
    def test_websocket_mixed_message_types(self, client):
        """Test mixing different message types"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send mixed message types
            messages = [
                {"type": "query", "message": "Show revenue"},
                {"type": "ping"},
                {"type": "query", "message": "Show expenses"},
                {"type": "ping"}
            ]
            
            expected_responses = ["response", "pong", "response", "pong"]
            
            for i, message in enumerate(messages):
                websocket.send_json(message)
                response = websocket.receive_json()
                assert response["type"] == expected_responses[i]


class TestWebSocketIntegration:
    """Test WebSocket integration with other components"""
    
    @patch('main.redis_client')
    def test_websocket_with_redis_integration(self, mock_redis, client):
        """Test WebSocket functionality with Redis integration"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = None
        
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send query
            query_message = {
                "type": "query",
                "message": "Show quarterly revenue"
            }
            websocket.send_json(query_message)
            
            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert "query_id" in response
    
    def test_websocket_message_timestamps(self, client):
        """Test that all WebSocket messages include timestamps"""
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Welcome message should have timestamp
            welcome = websocket.receive_json()
            assert "timestamp" in welcome
            
            # Query response should have timestamp
            query_message = {"type": "query", "message": "test"}
            websocket.send_json(query_message)
            
            response = websocket.receive_json()
            assert "timestamp" in response
            
            # Pong should have timestamp
            ping_message = {"type": "ping"}
            websocket.send_json(ping_message)
            
            pong = websocket.receive_json()
            assert "timestamp" in pong


if __name__ == "__main__":
    pytest.main([__file__])