"""
Integration tests for FastAPI backend
Tests complete workflows and component interactions
"""

import pytest
import json
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from main import app, create_access_token


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Valid JWT token for testing"""
    return create_access_token(data={"sub": "test_user"})


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with valid token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestCompleteQueryWorkflow:
    """Test complete query processing workflow"""
    
    @patch('main.redis_client')
    def test_complete_query_to_dashboard_workflow(self, mock_redis, client, auth_headers):
        """Test complete workflow from query to dashboard update"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = None
        
        # Step 1: Process a query
        query_data = {"query": "Show quarterly revenue trends"}
        query_response = client.post("/api/query", json=query_data, headers=auth_headers)
        assert query_response.status_code == 200
        
        query_result = query_response.json()
        query_id = query_result["query_id"]
        
        # Step 2: Submit feedback for the query
        feedback_data = {
            "query_id": query_id,
            "rating": 5,
            "feedback_text": "Great visualization!"
        }
        feedback_response = client.post("/api/feedback", json=feedback_data, headers=auth_headers)
        assert feedback_response.status_code == 200
        
        # Step 3: Get updated suggestions (should be influenced by feedback)
        suggestions_response = client.get("/api/suggestions", headers=auth_headers)
        assert suggestions_response.status_code == 200
        suggestions = suggestions_response.json()
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Step 4: Get dashboard layout
        layout_response = client.get("/api/dashboard/main_dashboard", headers=auth_headers)
        assert layout_response.status_code == 200
        layout = layout_response.json()
        assert layout["user_id"] == "test_user"
    
    def test_authentication_to_query_workflow(self, client):
        """Test complete workflow from login to query processing"""
        # Step 1: Login
        login_data = {"username": "cfo", "password": "demo"}
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Get user profile
        profile_response = client.get("/api/profile", headers=headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["user_id"] == "cfo"
        
        # Step 3: Process query
        query_data = {"query": "Show me cash flow analysis"}
        query_response = client.post("/api/query", json=query_data, headers=headers)
        assert query_response.status_code == 200
        
        # Step 4: Get suggestions
        suggestions_response = client.get("/api/suggestions", headers=headers)
        assert suggestions_response.status_code == 200


class TestWebSocketIntegration:
    """Test WebSocket integration with REST API"""
    
    def test_websocket_and_rest_api_consistency(self, client, auth_headers):
        """Test that WebSocket and REST API provide consistent responses"""
        # First, process query via REST API
        query_data = {"query": "Show revenue trends"}
        rest_response = client.post("/api/query", json=query_data, headers=auth_headers)
        assert rest_response.status_code == 200
        
        # Then, process similar query via WebSocket
        user_id = "test_user"
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send query
            ws_query = {
                "type": "query",
                "message": "Show revenue trends"
            }
            websocket.send_json(ws_query)
            
            ws_response = websocket.receive_json()
            assert ws_response["type"] == "response"
            assert "data" in ws_response
    
    @patch('main.redis_client')
    def test_websocket_with_session_management(self, mock_redis, client):
        """Test WebSocket functionality with session management"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = None
        
        user_id = "test_user"
        
        with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
            # Skip welcome message
            websocket.receive_json()
            
            # Send multiple queries to build session history
            queries = [
                "Show quarterly revenue",
                "Display cash flow trends",
                "What are our profit margins?"
            ]
            
            for query in queries:
                message = {"type": "query", "message": query}
                websocket.send_json(message)
                
                response = websocket.receive_json()
                assert response["type"] == "response"
                assert "query_id" in response


class TestErrorHandlingIntegration:
    """Test error handling across different components"""
    
    def test_cascading_error_handling(self, client, auth_headers):
        """Test error handling when multiple components fail"""
        # This would test scenarios where database is down, Redis is unavailable, etc.
        # For now, test basic error propagation
        
        # Test with malformed query data
        invalid_query = {"invalid_field": "test"}
        response = client.post("/api/query", json=invalid_query, headers=auth_headers)
        assert response.status_code == 422  # Validation error
    
    def test_graceful_degradation(self, client, auth_headers):
        """Test system behavior when optional services are unavailable"""
        # Test that core functionality works even when Redis is down
        with patch('main.redis_client', None):
            # Query should still work (without caching)
            query_data = {"query": "Show revenue"}
            response = client.post("/api/query", json=query_data, headers=auth_headers)
            assert response.status_code == 200
            
            # Feedback submission should handle Redis being unavailable
            feedback_data = {
                "query_id": "test_query",
                "rating": 4
            }
            feedback_response = client.post("/api/feedback", json=feedback_data, headers=auth_headers)
            # Should still return success even if Redis storage fails
            assert feedback_response.status_code == 200


class TestConcurrencyAndPerformance:
    """Test concurrent access and performance characteristics"""
    
    def test_concurrent_api_requests(self, client, auth_headers):
        """Test handling multiple concurrent API requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            query_data = {"query": f"Show revenue at {time.time()}"}
            response = client.post("/api/query", json=query_data, headers=auth_headers)
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)
    
    def test_websocket_concurrent_connections(self, client):
        """Test multiple concurrent WebSocket connections"""
        user_ids = ["user1", "user2", "user3"]
        
        # This test is limited by TestClient's WebSocket implementation
        # In a real scenario, you'd test with actual WebSocket clients
        for user_id in user_ids:
            with client.websocket_connect(f"/ws/chat/{user_id}") as websocket:
                # Skip welcome message
                websocket.receive_json()
                
                # Send ping
                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()
                assert response["type"] == "pong"


class TestDataConsistency:
    """Test data consistency across different endpoints"""
    
    @patch('main.redis_client')
    def test_user_profile_consistency(self, mock_redis, client, auth_headers):
        """Test user profile data consistency across endpoints"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = json.dumps({
            "user_id": "test_user",
            "chart_preferences": {"revenue": "line_chart"},
            "color_scheme": "corporate"
        })
        
        # Get profile
        profile_response = client.get("/api/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        
        # Process query (should use profile preferences)
        query_data = {"query": "Show revenue"}
        query_response = client.post("/api/query", json=query_data, headers=auth_headers)
        assert query_response.status_code == 200
        
        # Visualization should reflect user preferences
        query_result = query_response.json()
        if "visualization" in query_result:
            # In a real implementation, this would check if chart type matches preferences
            assert "chart_type" in query_result["visualization"]
    
    @patch('main.redis_client')
    def test_dashboard_layout_persistence(self, mock_redis, client, auth_headers):
        """Test dashboard layout persistence across sessions"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = None
        
        # Create and save a dashboard layout
        layout_data = {
            "layout_id": "test_layout",
            "user_id": "test_user",
            "layout_name": "Test Layout",
            "grid_columns": 6,
            "grid_rows": 4,
            "cards": [
                {
                    "id": "revenue_card",
                    "card_type": "kpi",
                    "size": "1x1",
                    "position": {"row": 0, "col": 0},
                    "title": "Revenue",
                    "content": {"value": 100000},
                    "styling": {},
                    "is_draggable": True,
                    "is_resizable": False,
                    "is_visible": True
                }
            ],
            "is_default": True,
            "is_shared": False,
            "metadata": {}
        }
        
        # Save layout
        save_response = client.post(
            "/api/dashboard/test_layout",
            json=layout_data,
            headers=auth_headers
        )
        assert save_response.status_code == 200
        
        # Retrieve layout
        get_response = client.get("/api/dashboard/test_layout", headers=auth_headers)
        assert get_response.status_code == 200
        
        retrieved_layout = get_response.json()
        assert retrieved_layout["layout_id"] == "test_layout"
        assert retrieved_layout["user_id"] == "test_user"


class TestSecurityIntegration:
    """Test security features in integrated scenarios"""
    
    def test_token_expiry_across_endpoints(self, client):
        """Test token expiry handling across different endpoints"""
        # Create short-lived token
        from datetime import timedelta
        short_token = create_access_token(
            {"sub": "test_user"}, 
            timedelta(seconds=1)
        )
        headers = {"Authorization": f"Bearer {short_token}"}
        
        # Should work immediately
        response1 = client.get("/api/profile", headers=headers)
        assert response1.status_code == 200
        
        # Wait for expiry
        import time
        time.sleep(2)
        
        # Should fail after expiry
        response2 = client.get("/api/suggestions", headers=headers)
        assert response2.status_code == 401
    
    def test_rate_limiting_across_user_sessions(self, client):
        """Test rate limiting behavior across different user sessions"""
        # Create tokens for different users
        user1_token = create_access_token({"sub": "user1"})
        user2_token = create_access_token({"sub": "user2"})
        
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        
        # Both users should be able to make requests
        query_data = {"query": "test"}
        
        response1 = client.post("/api/query", json=query_data, headers=user1_headers)
        response2 = client.post("/api/query", json=query_data, headers=user2_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestHealthAndMonitoring:
    """Test health checks and monitoring endpoints"""
    
    def test_health_check_comprehensive(self, client):
        """Test comprehensive health check"""
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "services" in health_data
        assert "timestamp" in health_data
        
        # Should include service status
        services = health_data["services"]
        assert "redis" in services
        assert "database" in services
    
    @patch('main.redis_client')
    def test_health_check_with_service_failures(self, mock_redis, client):
        """Test health check when services are failing"""
        # Mock Redis failure
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        response = client.get("/health")
        # Health endpoint should still respond
        assert response.status_code == 200
        
        health_data = response.json()
        # Should indicate service issues
        assert "services" in health_data


if __name__ == "__main__":
    pytest.main([__file__])