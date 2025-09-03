"""Tests for KIMI API client"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.kimi_client import (
    KimiClient,
    KimiAPIError,
    KimiAuthenticationError,
    KimiRateLimitError,
    KimiTimeoutError,
)
from src.models import KimiResponse


class TestKimiClient:
    """Test cases for KimiClient"""
    
    @pytest.fixture
    def kimi_client(self):
        """Create a KimiClient instance for testing"""
        return KimiClient(api_key="test-api-key")
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock KIMI API response data"""
        return {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "moonshot-v1-8k",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"metric_type": "revenue", "time_period": "this_year", "confidence_score": 0.9}'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 30,
                "total_tokens": 80
            }
        }
    
    def test_init_with_api_key(self):
        """Test KimiClient initialization with API key"""
        client = KimiClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.moonshot.ai/v1"
        assert client.timeout == 30
        assert client.max_retries == 3
    
    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="MOONSHOT API key is required"):
                KimiClient()
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, kimi_client, mock_response_data):
        """Test successful chat completion"""
        with patch.object(kimi_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data
            
            messages = [{"role": "user", "content": "Test query"}]
            response = await kimi_client.chat_completion(messages)
            
            assert isinstance(response, KimiResponse)
            assert response.id == "chatcmpl-test123"
            assert response.model == "moonshot-v1-8k"
            assert len(response.choices) == 1
            assert response.usage["total_tokens"] == 80
            
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_financial_intent_success(self, kimi_client, mock_response_data):
        """Test successful financial intent extraction"""
        with patch.object(kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_response = KimiResponse(**mock_response_data)
            mock_chat.return_value = mock_response
            
            intent_data = await kimi_client.extract_financial_intent("Show me revenue this year")
            
            assert intent_data["metric_type"] == "revenue"
            assert intent_data["time_period"] == "this_year"
            assert intent_data["confidence_score"] == 0.9
            
            mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_financial_entities_success(self, kimi_client):
        """Test successful financial entity extraction"""
        mock_entities_response = {
            "id": "chatcmpl-test123",
            "object": "chat.completion", 
            "created": 1234567890,
            "model": "moonshot-v1-8k",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '[{"entity_type": "metric", "entity_value": "revenue", "confidence_score": 0.9, "synonyms": ["sales"], "original_text": "revenue"}]'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
        }
        
        with patch.object(kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_response = KimiResponse(**mock_entities_response)
            mock_chat.return_value = mock_response
            
            entities = await kimi_client.extract_financial_entities("Show me revenue")
            
            assert len(entities) == 1
            assert entities[0]["entity_type"] == "metric"
            assert entities[0]["entity_value"] == "revenue"
            assert entities[0]["confidence_score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_detect_ambiguities_success(self, kimi_client):
        """Test successful ambiguity detection"""
        mock_ambiguities_response = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "moonshot-v1-8k",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '[{"ambiguity_type": "time_period", "description": "Time period unclear", "possible_interpretations": ["this quarter", "last quarter"], "confidence_score": 0.8, "suggested_clarification": "Which quarter?"}]'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
        }
        
        with patch.object(kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_response = KimiResponse(**mock_ambiguities_response)
            mock_chat.return_value = mock_response
            
            ambiguities = await kimi_client.detect_ambiguities("Show me performance")
            
            assert len(ambiguities) == 1
            assert ambiguities[0]["ambiguity_type"] == "time_period"
            assert ambiguities[0]["confidence_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_make_request_authentication_error(self, kimi_client):
        """Test authentication error handling"""
        with patch.object(kimi_client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_request.return_value = mock_response
            
            with pytest.raises(KimiAuthenticationError):
                await kimi_client._make_request("POST", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, kimi_client):
        """Test rate limit error handling"""
        with patch.object(kimi_client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_request.return_value = mock_response
            
            with pytest.raises(KimiRateLimitError):
                await kimi_client._make_request("POST", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_retry_logic(self, kimi_client):
        """Test retry logic for server errors"""
        with patch.object(kimi_client.client, 'request', new_callable=AsyncMock) as mock_request:
            # First call returns 500, second call succeeds
            mock_response_error = MagicMock()
            mock_response_error.status_code = 500
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"success": True}
            
            mock_request.side_effect = [mock_response_error, mock_response_success]
            
            result = await kimi_client._make_request("POST", "/test")
            assert result == {"success": True}
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, kimi_client):
        """Test successful health check"""
        with patch.object(kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_response = MagicMock()
            mock_response.choices = [{"message": {"content": "Hello"}}]
            mock_chat.return_value = mock_response
            
            is_healthy = await kimi_client.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, kimi_client):
        """Test health check failure"""
        with patch.object(kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = KimiAPIError("API error")
            
            is_healthy = await kimi_client.health_check()
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test KimiClient as async context manager"""
        async with KimiClient(api_key="test-key") as client:
            assert client.api_key == "test-key"
        # Client should be closed after exiting context