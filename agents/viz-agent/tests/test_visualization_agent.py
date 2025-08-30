"""
Unit tests for the main Visualization Agent
"""

import pytest
import asyncio
from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest, ExportConfig, ExportFormat


class TestVisualizationAgent:
    """Test main visualization agent functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.agent = VisualizationAgent()
    
    @pytest.mark.asyncio
    async def test_process_simple_visualization_request(self):
        """Test processing a simple visualization request"""
        request = VisualizationRequest(
            request_id="test_001",
            user_id="test_user",
            query_intent={
                "metric_type": "revenue",
                "time_period": "monthly",
                "title": "Monthly Revenue"
            },
            data=[
                {"month": "Jan", "revenue": 100000},
                {"month": "Feb", "revenue": 120000},
                {"month": "Mar", "revenue": 110000}
            ]
        )
        
        response = await self.agent.process_visualization_request(request)
        
        assert response.success is True
        assert response.request_id == "test_001"
        assert response.chart_spec is not None
        assert response.chart_html != ""
        assert response.chart_json != {}
        assert response.processing_time_ms > 0
        assert response.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_request_with_preferences(self):
        """Test processing request with user preferences"""
        request = VisualizationRequest(
            request_id="test_002",
            user_id="test_user",
            query_intent={
                "metric_type": "budget_variance",
                "title": "Budget vs Actual"
            },
            data=[
                {"department": "Sales", "budget": 100000, "actual": 95000},
                {"department": "Marketing", "budget": 50000, "actual": 55000}
            ],
            preferences={
                "preferred_chart_type": "bar",
                "color_scheme": "financial",
                "show_legend": True,
                "chart_height": 500
            }
        )
        
        response = await self.agent.process_visualization_request(request)
        
        assert response.success is True
        assert response.chart_spec.chart_config.chart_type.value == "bar"
        assert response.chart_spec.chart_config.color_scheme == "financial"
        assert response.chart_spec.chart_config.height == 500
    
    @pytest.mark.asyncio
    async def test_process_request_with_export(self):
        """Test processing request with export configuration"""
        request = VisualizationRequest(
            request_id="test_003",
            user_id="test_user",
            query_intent={"metric_type": "cash_flow"},
            data=[
                {"period": "Q1", "cash_flow": 50000},
                {"period": "Q2", "cash_flow": 75000}
            ],
            export_config=ExportConfig(
                format=ExportFormat.PNG,
                filename="cash_flow_chart.png"
            )
        )
        
        response = await self.agent.process_visualization_request(request)
        
        assert response.success is True
        assert "png" in response.export_urls
        assert response.export_urls["png"] != ""
    
    @pytest.mark.asyncio
    async def test_process_large_dataset(self):
        """Test processing large dataset with optimization"""
        # Create large dataset
        large_data = [{"x": i, "y": i * 2} for i in range(15000)]
        
        request = VisualizationRequest(
            request_id="test_004",
            user_id="test_user",
            query_intent={"metric_type": "performance"},
            data=large_data
        )
        
        response = await self.agent.process_visualization_request(request)
        
        assert response.success is True
        # Data should be optimized (reduced in size)
        assert len(response.chart_spec.data.data) < len(large_data)
    
    @pytest.mark.asyncio
    async def test_get_chart_alternatives(self):
        """Test getting alternative chart types"""
        request = VisualizationRequest(
            request_id="test_005",
            user_id="test_user",
            query_intent={"metric_type": "revenue"},
            data=[
                {"month": "Jan", "revenue": 100000},
                {"month": "Feb", "revenue": 120000}
            ]
        )
        
        alternatives = await self.agent.get_chart_alternatives(request)
        
        assert len(alternatives) > 0
        assert all("chart_type" in alt for alt in alternatives)
        assert all("name" in alt for alt in alternatives)
        assert all("description" in alt for alt in alternatives)
    
    @pytest.mark.asyncio
    async def test_export_multiple_formats(self):
        """Test exporting chart in multiple formats"""
        request = VisualizationRequest(
            request_id="test_006",
            user_id="test_user",
            query_intent={"metric_type": "revenue"},
            data=[
                {"month": "Jan", "revenue": 100000},
                {"month": "Feb", "revenue": 120000}
            ]
        )
        
        formats = ["png", "html", "csv"]
        result = await self.agent.export_chart_multiple_formats(request, formats)
        
        assert result["success"] is True
        assert "exports" in result
        assert "urls" in result
        assert len(result["exports"]) == 3
    
    def test_performance_recommendations(self):
        """Test getting performance recommendations"""
        recommendations = self.agent.get_performance_recommendations(5000, "scatter")
        
        assert "use_webgl" in recommendations
        assert recommendations["use_webgl"] is True  # Should recommend WebGL for large scatter
    
    def test_performance_recommendations_invalid_chart_type(self):
        """Test performance recommendations with invalid chart type"""
        recommendations = self.agent.get_performance_recommendations(1000, "invalid_type")
        
        assert "error" in recommendations
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check"""
        health_status = await self.agent.health_check()
        
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "unhealthy"]
        assert "components" in health_status
        assert "cache_size" in health_status
        assert "test_processing_time_ms" in health_status
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self):
        """Test response caching"""
        request = VisualizationRequest(
            request_id="test_007",
            user_id="test_user",
            query_intent={"metric_type": "revenue"},
            data=[
                {"month": "Jan", "revenue": 100000},
                {"month": "Feb", "revenue": 120000}
            ]
        )
        
        # First request
        response1 = await self.agent.process_visualization_request(request)
        first_processing_time = response1.processing_time_ms
        
        # Second identical request (should be cached)
        response2 = await self.agent.process_visualization_request(request)
        second_processing_time = response2.processing_time_ms
        
        assert response1.success is True
        assert response2.success is True
        assert response1.request_id == response2.request_id
        # Second request should be faster due to caching
        assert second_processing_time <= first_processing_time
    
    @pytest.mark.asyncio
    async def test_error_handling_empty_data(self):
        """Test error handling with empty data"""
        request = VisualizationRequest(
            request_id="test_008",
            user_id="test_user",
            query_intent={"metric_type": "revenue"},
            data=[]  # Empty data
        )
        
        response = await self.agent.process_visualization_request(request)
        
        # Should handle empty data gracefully
        assert response.request_id == "test_008"
        # May succeed with empty chart or fail gracefully
        if not response.success:
            assert response.error_message is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self):
        """Test error handling with invalid data structure"""
        request = VisualizationRequest(
            request_id="test_009",
            user_id="test_user",
            query_intent={"metric_type": "revenue"},
            data=[
                {"invalid": "structure"},
                {"different": "keys"}
            ]
        )
        
        response = await self.agent.process_visualization_request(request)
        
        # Should handle gracefully
        assert response.request_id == "test_009"
        # May succeed with basic chart or provide error
        if not response.success:
            assert response.error_message is not None
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        request1 = VisualizationRequest(
            request_id="test_010",
            user_id="user1",
            query_intent={"metric_type": "revenue"},
            data=[{"x": 1, "y": 2}]
        )
        
        request2 = VisualizationRequest(
            request_id="test_011",  # Different request ID
            user_id="user1",
            query_intent={"metric_type": "revenue"},
            data=[{"x": 1, "y": 2}]  # Same data
        )
        
        key1 = self.agent._generate_cache_key(request1)
        key2 = self.agent._generate_cache_key(request2)
        
        # Should generate same cache key for same user, intent, and data
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) > 0
    
    def test_chart_configuration_creation(self):
        """Test chart configuration creation"""
        query_intent = {
            "metric_type": "revenue",
            "time_period": "monthly",
            "title": "Monthly Revenue Analysis"
        }
        
        preferences = {
            "color_scheme": "professional",
            "chart_height": 600,
            "show_grid": False
        }
        
        from src.models import ChartType
        config = self.agent._create_chart_configuration(
            ChartType.LINE, query_intent, preferences
        )
        
        assert config.chart_type == ChartType.LINE
        assert config.color_scheme == "professional"
        assert config.height == 600
        assert config.show_grid is False
        assert "Revenue" in config.title
    
    def test_interactive_configuration_creation(self):
        """Test interactive configuration creation"""
        preferences = {
            "enable_zoom": False,
            "enable_hover": True,
            "drill_down_enabled": True,
            "drill_down_levels": ["year", "quarter", "month"]
        }
        
        config = self.agent._create_interactive_configuration(preferences)
        
        assert config.enable_zoom is False
        assert config.enable_hover is True
        assert config.drill_down_enabled is True
        assert config.drill_down_levels == ["year", "quarter", "month"]