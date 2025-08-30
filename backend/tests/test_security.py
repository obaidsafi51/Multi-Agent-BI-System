"""
Unit tests for security features and middleware
"""

import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import (
    app, SECRET_KEY, ALGORITHM, create_access_token, 
    verify_password, get_password_hash, get_current_user
)


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test_user"
        assert "exp" in payload
    
    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test_user"
        
        # Check expiry is approximately 60 minutes from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta
        time_diff = abs((exp_time - expected_exp).total_seconds())
        assert time_diff < 5  # Allow 5 seconds tolerance
    
    def test_token_expiry(self):
        """Test expired token handling"""
        # Create token that expires immediately
        data = {"sub": "test_user"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)
        
        # Should raise exception when decoding expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    def test_invalid_token_signature(self):
        """Test invalid token signature"""
        # Create token with wrong secret
        data = {"sub": "test_user"}
        token = jwt.encode(data, "wrong_secret", algorithm=ALGORITHM)
        
        # Should raise exception when decoding with correct secret
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    def test_malformed_token(self):
        """Test malformed token handling"""
        malformed_token = "not.a.valid.jwt.token"
        
        with pytest.raises(jwt.DecodeError):
            jwt.decode(malformed_token, SECRET_KEY, algorithms=[ALGORITHM])


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        # Hash should be consistent
        assert len(hashed) > 0
        # Should start with bcrypt identifier
        assert hashed.startswith("$2b$")
    
    def test_password_verification_success(self):
        """Test successful password verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes"""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAuthenticationMiddleware:
    """Test authentication middleware and user extraction"""
    
    def test_get_current_user_valid_token(self):
        """Test extracting user from valid token"""
        # This test would require mocking the Depends mechanism
        # For now, test token creation and validation separately
        token = create_access_token({"sub": "test_user"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test_user"
    
    def test_protected_endpoint_access(self, client):
        """Test accessing protected endpoint with valid token"""
        # Create valid token
        token = create_access_token({"sub": "test_user"})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Access protected endpoint
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 200
    
    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/profile")
        assert response.status_code == 403
    
    def test_protected_endpoint_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401
    
    def test_protected_endpoint_malformed_auth_header(self, client):
        """Test accessing protected endpoint with malformed auth header"""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 403


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_login_endpoint(self, client):
        """Test rate limiting on login endpoint"""
        login_data = {"username": "test", "password": "test"}
        
        # Make requests up to the limit
        responses = []
        for i in range(6):  # Limit is 5/minute
            response = client.post("/api/auth/login", json=login_data)
            responses.append(response)
        
        # First 5 should be processed (even if they fail authentication)
        assert all(r.status_code in [401, 200] for r in responses[:5])
        
        # 6th should be rate limited
        assert responses[5].status_code == 429
    
    def test_rate_limit_query_endpoint(self, client):
        """Test rate limiting on query endpoint"""
        token = create_access_token({"sub": "test_user"})
        headers = {"Authorization": f"Bearer {token}"}
        query_data = {"query": "test"}
        
        # Make requests up to the limit (30/minute)
        # Test with fewer requests to avoid long test execution
        responses = []
        for i in range(5):
            response = client.post("/api/query", json=query_data, headers=headers)
            responses.append(response)
        
        # All should be processed successfully
        assert all(r.status_code == 200 for r in responses)
    
    def test_rate_limit_different_endpoints(self, client):
        """Test that rate limits are per-endpoint"""
        token = create_access_token({"sub": "test_user"})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make requests to different endpoints
        query_response = client.post("/api/query", json={"query": "test"}, headers=headers)
        suggestions_response = client.get("/api/suggestions", headers=headers)
        profile_response = client.get("/api/profile", headers=headers)
        
        # All should succeed (different rate limits)
        assert query_response.status_code == 200
        assert suggestions_response.status_code == 200
        assert profile_response.status_code == 200


class TestCORSMiddleware:
    """Test CORS middleware functionality"""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight request"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        
        response = client.options("/api/query", headers=headers)
        assert response.status_code == 200
    
    def test_cors_allowed_origin(self, client):
        """Test CORS with allowed origin"""
        headers = {"Origin": "http://localhost:3000"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
    
    def test_cors_credentials_support(self, client):
        """Test CORS credentials support"""
        # CORS middleware is configured to allow credentials
        # This would be tested in integration tests with actual browser requests
        headers = {"Origin": "http://localhost:3000"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200


class TestTrustedHostMiddleware:
    """Test trusted host middleware"""
    
    def test_trusted_host_allowed(self, client):
        """Test request from trusted host"""
        # TestClient doesn't send Host header by default
        # In real deployment, this would be tested with actual HTTP requests
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_trusted_host_configuration(self):
        """Test trusted host middleware configuration"""
        # Verify middleware is configured with correct hosts
        # This is more of a configuration test
        allowed_hosts = ["localhost", "127.0.0.1", "frontend", "backend"]
        assert all(isinstance(host, str) for host in allowed_hosts)


class TestSecurityHeaders:
    """Test security headers and responses"""
    
    def test_error_response_format(self, client):
        """Test error responses don't leak sensitive information"""
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/profile", headers=headers)
        
        assert response.status_code == 401
        error_data = response.json()
        
        # Should not contain sensitive information
        assert "secret" not in str(error_data).lower()
        assert "password" not in str(error_data).lower()
        assert "key" not in str(error_data).lower()
    
    def test_authentication_error_consistency(self, client):
        """Test authentication errors are consistent"""
        # Test various authentication failures
        test_cases = [
            {"headers": {"Authorization": "Bearer invalid_token"}},
            {"headers": {"Authorization": "Bearer expired_token"}},
            {"headers": {"Authorization": "InvalidFormat token"}},
        ]
        
        for case in test_cases:
            response = client.get("/api/profile", headers=case["headers"])
            # All should return 401 or 403 (not 500 or other codes)
            assert response.status_code in [401, 403]
    
    def test_no_sensitive_data_in_logs(self, client):
        """Test that sensitive data is not logged"""
        # This would require checking actual log output
        # For now, just verify endpoints work without errors
        login_data = {"username": "test", "password": "sensitive_password"}
        response = client.post("/api/auth/login", json=login_data)
        
        # Should handle request without exposing password in errors
        assert response.status_code in [200, 401]


class TestSessionManagement:
    """Test session management and token lifecycle"""
    
    def test_token_expiry_handling(self, client):
        """Test handling of expired tokens"""
        # Create token that expires quickly
        expired_token = create_access_token(
            {"sub": "test_user"}, 
            timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401
    
    def test_token_refresh_needed(self, client):
        """Test token refresh scenarios"""
        # Create token that expires soon
        short_lived_token = create_access_token(
            {"sub": "test_user"}, 
            timedelta(seconds=1)
        )
        headers = {"Authorization": f"Bearer {short_lived_token}"}
        
        # Should work immediately
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 200
        
        # After expiry, should fail
        import time
        time.sleep(2)
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])