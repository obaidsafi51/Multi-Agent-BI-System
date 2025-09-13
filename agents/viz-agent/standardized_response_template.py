"""
Template for creating standardized Visualization Agent responses
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

# Import standardized models from local shared package
from shared.models.workflow import VisualizationResponse, AgentMetadata, ErrorResponse
from shared.models.visualization import ChartConfiguration, ChartData, ChartSeries

async def create_visualization_standardized(data: list, intent: dict) -> VisualizationResponse:
    """Create visualization using standardized response format"""
    
    start_time = datetime.utcnow()
    operation_id = f"viz_op_{int(datetime.utcnow().timestamp() * 1000)}"
    
    try:
        # Create chart configuration using standardized format
        chart_config = {
            "chart_type": "line",
            "title": "Quarterly Revenue",
            "x_axis_label": "Period",
            "y_axis_label": "Revenue (USD)",
            "color_scheme": "corporate",
            "responsive": True
        }
        
        # Create chart data using standardized format  
        chart_data = {
            "datasets": [
                {
                    "label": "Revenue",
                    "data": [1000000, 1200000, 1100000],
                    "backgroundColor": "#1f77b4"
                }
            ],
            "labels": ["Q1", "Q2", "Q3"]
        }
        
        # Create dashboard cards
        dashboard_cards = [
            {
                "type": "kpi",
                "title": "Total Revenue", 
                "value": "$3.3M",
                "change": "+12.5%",
                "trend": "up"
            }
        ]
        
        # Create standardized agent metadata
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="viz-agent",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="success"
        )
        
        # Return standardized response
        return VisualizationResponse(
            success=True,
            agent_metadata=agent_metadata,
            chart_config=chart_config,
            chart_data=chart_data,
            dashboard_cards=dashboard_cards,
            export_options={
                "formats": ["png", "pdf", "svg"],
                "sizes": ["small", "medium", "large"]
            }
        )
        
    except Exception as e:
        # Create error response using standardized format
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="viz-agent",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="error"
        )
        
        return VisualizationResponse(
            success=False,
            agent_metadata=agent_metadata,
            error=ErrorResponse(
                error_type="visualization_error",
                message=str(e),
                recovery_action="retry",
                suggestions=["Check data format", "Verify chart configuration"]
            )
        )
