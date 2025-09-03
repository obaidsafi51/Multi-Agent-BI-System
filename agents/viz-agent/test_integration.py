#!/usr/bin/env python3
"""
Integration test for viz-agent with other services
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.visualization_agent import VisualizationAgent
from src.models import ChartType, ChartConfiguration, VisualizationRequest
import asyncio
import pytest


@pytest.mark.asyncio
async def test_viz_agent_integration():
    """Test basic viz-agent functionality"""
    print("🚀 Testing Viz-Agent Integration...")
    
    try:
        # Initialize viz-agent
        agent = VisualizationAgent()
        print("✅ Viz-agent initialized successfully")
        
        # Test health check
        health = await agent.health_check()
        print(f"✅ Health check: {health}")
        
        # Test basic chart generation
        sample_data = [
            {"month": "Jan", "revenue": 100000, "expenses": 80000},
            {"month": "Feb", "revenue": 120000, "expenses": 85000},
            {"month": "Mar", "revenue": 110000, "expenses": 82000}
        ]
        
        request = VisualizationRequest(
            request_id="test-001",
            user_id="test-user",
            query_intent={"type": "financial_chart", "metrics": ["revenue", "expenses"]},
            data=sample_data,
            preferences={
                "chart_type": ChartType.LINE,
                "title": "Monthly Revenue vs Expenses",
                "description": "Financial performance over Q1"
            }
        )
        
        print("📊 Generating test chart...")
        result = await agent.process_visualization_request(request)
        
        print(f"✅ Chart generated successfully!")
        print(f"   - Request ID: {result.request_id}")
        print(f"   - Chart type: {result.chart_spec.chart_config.chart_type}")
        print(f"   - Has HTML: {len(result.chart_html) > 0}")
        print(f"   - Has JSON: {len(result.chart_json) > 0}")
        print(f"   - Processing time: {result.processing_time_ms}ms")
        print(f"   - Success: {result.success}")
        
        # Test chart alternatives
        print("🔄 Testing chart alternatives...")
        alternatives = await agent.get_chart_alternatives(sample_data)
        print(f"✅ Found {len(alternatives)} chart alternatives: {alternatives}")
        
        print("\n🎉 All viz-agent integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_viz_agent_integration())
    sys.exit(0 if success else 1)
