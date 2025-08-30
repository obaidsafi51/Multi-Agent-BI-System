"""Tests for NLP Agent service"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nlp_agent import NLPAgent
from src.models import ProcessingResult, QueryContext, QueryIntent


class TestNLPAgent:
    """Test cases for NLPAgent"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.get = AsyncMock()
        return mock_redis
    
    @pytest.fixture
    def nlp_agent(self, mock_redis):
        """Create NLPAgent instance with mocked dependencies"""
        with patch('src.nlp_agent.redis.from_url', return_value=mock_redis):
            agent = NLPAgent(
                kimi_api_key="test-key",
                redis_url="redis://localhost:6379",
                rabbitmq_url="amqp://localhost:5672"
            )
            agent.redis_client = mock_redis
            return agent
    
    @pytest.fixture
    def sample_processing_result(self):
        """Sample processing result"""
        query_context = QueryContext(
            user_id="user123",
            session_id="session456",
            query_id="query789",
            original_query="Show me revenue",
            processed_query="show me revenue",
            intent=QueryIntent(
                metric_type="revenue",
                time_period="this_year",
                confidence_score=0.9
            )
        )
        
        return ProcessingResult(
            success=True,
            query_context=query_context,
            processing_time_ms=500,
            kimi_usage={"total_requests": 3}
        )
    
    @pytest.mark.asyncio
    async def test_start_success(self, nlp_agent):
        """Test successful agent startup"""
        with patch.object(nlp_agent.kimi_client, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            await nlp_agent.start()
            
            assert nlp_agent.is_running is True
            mock_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_kimi_health_check_fails(self, nlp_agent):
        """Test agent startup with KIMI health check failure"""
        with patch.object(nlp_agent.kimi_client, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = False
            
            with pytest.raises(Exception, match="KIMI API health check failed"):
                await nlp_agent.start()
            
            assert nlp_agent.is_running is False
    
    @pytest.mark.asyncio
    async def test_stop(self, nlp_agent):
        """Test agent shutdown"""
        nlp_agent.is_running = True
        
        with patch.object(nlp_agent.kimi_client, 'close', new_callable=AsyncMock) as mock_close:
            await nlp_agent.stop()
            
            assert nlp_agent.is_running is False
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, nlp_agent, sample_processing_result):
        """Test successful query processing"""
        nlp_agent.is_running = True
        
        with patch.object(nlp_agent.query_parser, 'parse_query', new_callable=AsyncMock) as mock_parse:
            with patch.object(nlp_agent, '_store_mcp_context', new_callable=AsyncMock) as mock_store:
                with patch.object(nlp_agent, '_send_agent_contexts', new_callable=AsyncMock) as mock_send:
                    mock_parse.return_value = sample_processing_result
                    
                    result = await nlp_agent.process_query(
                        query="Show me revenue",
                        user_id="user123",
                        session_id="session456"
                    )
                    
                    assert result.success is True
                    assert result.query_context is not None
                    mock_parse.assert_called_once()
                    mock_store.assert_called_once()
                    mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_not_running(self, nlp_agent):
        """Test query processing when agent is not running"""
        nlp_agent.is_running = False
        
        result = await nlp_agent.process_query(
            query="Show me revenue",
            user_id="user123",
            session_id="session456"
        )
        
        assert result.success is False
        assert "not running" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_query_parsing_failure(self, nlp_agent):
        """Test query processing with parsing failure"""
        nlp_agent.is_running = True
        
        failed_result = ProcessingResult(
            success=False,
            error_message="Parsing failed",
            processing_time_ms=100
        )
        
        with patch.object(nlp_agent.query_parser, 'parse_query', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = failed_result
            
            result = await nlp_agent.process_query(
                query="Show me revenue",
                user_id="user123",
                session_id="session456"
            )
            
            assert result.success is False
            assert result.error_message == "Parsing failed"
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_new_user(self, nlp_agent):
        """Test getting suggestions for new user"""
        nlp_agent.redis_client.get.return_value = None
        
        suggestions = await nlp_agent.get_query_suggestions("new_user")
        
        assert len(suggestions) > 0
        assert any("revenue" in suggestion.lower() for suggestion in suggestions)
        assert any("cash flow" in suggestion.lower() for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_existing_user(self, nlp_agent):
        """Test getting personalized suggestions for existing user"""
        # Mock user history
        history_data = json.dumps([
            "Show me revenue this year",
            "What's our profit margin?",
            "Compare cash flow Q1 vs Q2"
        ])
        nlp_agent.redis_client.get.return_value = history_data
        
        # Mock KIMI response
        mock_suggestions = ["Show me revenue trends", "Analyze profit by department"]
        
        with patch.object(nlp_agent.kimi_client, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_response = MagicMock()
            mock_response.choices = [{"message": {"content": json.dumps(mock_suggestions)}}]
            mock_chat.return_value = mock_response
            
            suggestions = await nlp_agent.get_query_suggestions("existing_user")
            
            assert suggestions == mock_suggestions
            mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_mcp_context(self, nlp_agent, sample_processing_result):
        """Test storing MCP context in Redis"""
        query_context = sample_processing_result.query_context
        
        await nlp_agent._store_mcp_context(query_context)
        
        # Verify Redis calls
        assert nlp_agent.redis_client.setex.call_count == 2  # context + session
        
        # Check context storage call
        context_call = nlp_agent.redis_client.setex.call_args_list[0]
        assert context_call[0][0] == f"mcp_context:{query_context.query_id}"
        assert context_call[0][1] == 3600  # TTL
        
        # Check session storage call
        session_call = nlp_agent.redis_client.setex.call_args_list[1]
        assert session_call[0][0] == f"session_context:{query_context.session_id}"
        assert session_call[0][1] == 1800  # TTL
    
    @pytest.mark.asyncio
    async def test_send_agent_contexts(self, nlp_agent, sample_processing_result):
        """Test sending contexts to other agents"""
        query_context = sample_processing_result.query_context
        
        await nlp_agent._send_agent_contexts(query_context)
        
        # Should store 3 contexts (data, viz, personalization)
        assert nlp_agent.redis_client.setex.call_count == 3
        
        # Verify context keys
        calls = nlp_agent.redis_client.setex.call_args_list
        context_keys = [call[0][0] for call in calls]
        
        assert any("data_agent" in key for key in context_keys)
        assert any("visualization_agent" in key for key in context_keys)
        assert any("personalization_agent" in key for key in context_keys)
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, nlp_agent):
        """Test health check with all components healthy"""
        nlp_agent.is_running = True
        
        with patch.object(nlp_agent.kimi_client, 'health_check', new_callable=AsyncMock) as mock_kimi_health:
            mock_kimi_health.return_value = True
            
            health_status = await nlp_agent.health_check()
            
            assert health_status["overall_status"] == "healthy"
            assert health_status["is_running"] is True
            assert health_status["components"]["kimi_api"]["status"] == "healthy"
            assert health_status["components"]["redis"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_kimi_unhealthy(self, nlp_agent):
        """Test health check with KIMI API unhealthy"""
        nlp_agent.is_running = True
        
        with patch.object(nlp_agent.kimi_client, 'health_check', new_callable=AsyncMock) as mock_kimi_health:
            mock_kimi_health.return_value = False
            
            health_status = await nlp_agent.health_check()
            
            assert health_status["overall_status"] == "degraded"
            assert health_status["components"]["kimi_api"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_redis_error(self, nlp_agent):
        """Test health check with Redis error"""
        nlp_agent.is_running = True
        nlp_agent.redis_client.ping.side_effect = Exception("Redis connection failed")
        
        with patch.object(nlp_agent.kimi_client, 'health_check', new_callable=AsyncMock) as mock_kimi_health:
            mock_kimi_health.return_value = True
            
            health_status = await nlp_agent.health_check()
            
            assert health_status["overall_status"] == "error"
            assert health_status["components"]["redis"]["status"] == "error"
            assert "Redis connection failed" in health_status["components"]["redis"]["details"]