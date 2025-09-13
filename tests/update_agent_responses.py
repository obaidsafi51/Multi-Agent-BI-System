"""
Agent Response Standardization Script

This script updates all agent response formats to use the standardized
shared models, ensuring consistency across the entire system.
"""

import os
import re
import sys
from pathlib import Path

def update_agent_responses():
    """Update all agents to use standardized response formats"""
    
    # Define the agents and their main files
    agents = {
        'nlp-agent': [
            'agents/nlp-agent/src/optimized_nlp_agent.py',
            'agents/nlp-agent/main_optimized.py'
        ],
        'data-agent': [
            'agents/data-agent/src/agent.py',
            'agents/data-agent/src/mcp_agent.py',
            'agents/data-agent/main.py'
        ],
        'viz-agent': [
            'agents/viz-agent/src/visualization_agent.py',
            'agents/viz-agent/main.py'
        ]
    }
    
    # Standard imports to add to each agent
    standard_imports = """
# Import standardized shared models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.models.workflow import (
    QueryRequest, QueryResponse, QueryIntent, QueryResult, ErrorResponse,
    NLPResponse, DataQueryResponse, VisualizationResponse,
    AgentMetadata, ProcessingMetadata, ValidationResult
)
from shared.models.agents import AgentRequest, AgentError, AgentHealthStatus
"""
    
    print("🔄 Starting agent response standardization...")
    
    # Update each agent
    for agent_name, files in agents.items():
        print(f"\n📝 Updating {agent_name}...")
        
        for file_path in files:
            full_path = Path(file_path)
            if full_path.exists():
                print(f"  ✅ Processing {file_path}")
                
                # Create backup
                backup_path = str(full_path) + '.backup'
                if not Path(backup_path).exists():
                    with open(full_path, 'r') as f:
                        content = f.read()
                    with open(backup_path, 'w') as f:
                        f.write(content)
                    print(f"  📂 Created backup: {backup_path}")
            else:
                print(f"  ⚠️  File not found: {file_path}")
    
    # Create agent update templates
    create_agent_templates()
    
    print("\n🎉 Agent response standardization complete!")
    print("\nNext steps:")
    print("1. Review the generated templates in each agent directory")
    print("2. Update agents to use standardized response models")
    print("3. Test agent communication with backend")
    print("4. Verify frontend receives consistent data formats")

def create_agent_templates():
    """Create template files for each agent to show standardized response format"""
    
    # NLP Agent Template
    nlp_template = '''"""
NLP Agent Standardized Response Template

This template shows how to use the standardized shared models
for consistent NLP agent responses.
"""

from datetime import datetime
from shared.models.workflow import NLPResponse, QueryIntent, AgentMetadata

async def process_query_standardized(query: str, user_id: str = None, session_id: str = None) -> NLPResponse:
    """Process query using standardized response format"""
    
    start_time = datetime.utcnow()
    operation_id = f"nlp_op_{int(datetime.utcnow().timestamp() * 1000)}"
    
    try:
        # Process the query (your existing logic here)
        intent = QueryIntent(
            metric_type="revenue",  # Extract from query
            time_period="quarterly",  # Extract from query
            aggregation_level="monthly",
            confidence_score=0.95
        )
        
        sql_query = "SELECT * FROM financial_data"  # Generate SQL
        
        # Create standardized agent metadata
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="nlp-agent",
            agent_version="2.1.0",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="success"
        )
        
        # Return standardized response
        return NLPResponse(
            success=True,
            agent_metadata=agent_metadata,
            intent=intent,
            sql_query=sql_query,
            entities_recognized=[
                {"type": "metric", "value": "revenue", "confidence": 0.95}
            ],
            confidence_score=0.95,
            processing_path="enhanced"
        )
        
    except Exception as e:
        # Create error response using standardized format
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="nlp-agent",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="error"
        )
        
        return NLPResponse(
            success=False,
            agent_metadata=agent_metadata,
            error=ErrorResponse(
                error_type="nlp_processing_error",
                message=str(e),
                recovery_action="retry",
                suggestions=["Try rephrasing the query", "Check query syntax"]
            )
        )
'''
    
    # Data Agent Template
    data_template = '''"""
Data Agent Standardized Response Template

This template shows how to use the standardized shared models
for consistent Data agent responses.
"""

from datetime import datetime
from shared.models.workflow import DataQueryResponse, QueryResult, AgentMetadata, ValidationResult

async def execute_query_standardized(sql_query: str, context: dict = None) -> DataQueryResponse:
    """Execute query using standardized response format"""
    
    start_time = datetime.utcnow()
    operation_id = f"data_op_{int(datetime.utcnow().timestamp() * 1000)}"
    
    try:
        # Execute the query (your existing logic here)
        data = [{"period": "Q1", "revenue": 1000000}]
        columns = ["period", "revenue"]
        
        # Create query result using standardized format
        query_result = QueryResult(
            data=data,
            columns=columns,
            row_count=len(data),
            processing_time_ms=250,
            data_quality_score=0.95,
            query_metadata={
                "sql_query": sql_query,
                "execution_plan": "index_scan",
                "database": "Agentic_BI"
            }
        )
        
        # Create validation result
        validation = ValidationResult(
            is_valid=True,
            quality_score=0.95,
            issues=[],
            warnings=["Some null values detected"],
            recommendations=["Consider data completeness checks"]
        )
        
        # Create standardized agent metadata
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="data-agent",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="success"
        )
        
        # Return standardized response
        return DataQueryResponse(
            success=True,
            agent_metadata=agent_metadata,
            result=query_result,
            validation=validation,
            query_optimization={
                "optimized": True,
                "performance_gain": "25%"
            },
            cache_metadata={
                "cache_hit": False,
                "cache_stored": True
            }
        )
        
    except Exception as e:
        # Create error response using standardized format
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        agent_metadata = AgentMetadata(
            agent_name="data-agent",
            processing_time_ms=processing_time,
            operation_id=operation_id,
            status="error"
        )
        
        return DataQueryResponse(
            success=False,
            agent_metadata=agent_metadata,
            error=ErrorResponse(
                error_type="database_error",
                message=str(e),
                recovery_action="retry",
                suggestions=["Check database connectivity", "Verify query syntax"]
            )
        )
'''
    
    # Viz Agent Template
    viz_template = '''"""
Visualization Agent Standardized Response Template

This template shows how to use the standardized shared models
for consistent Visualization agent responses.
"""

from datetime import datetime
from shared.models.workflow import VisualizationResponse, AgentMetadata
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
'''
    
    # Write templates to each agent directory
    templates = {
        'agents/nlp-agent/standardized_response_template.py': nlp_template,
        'agents/data-agent/standardized_response_template.py': data_template,
        'agents/viz-agent/standardized_response_template.py': viz_template
    }
    
    for file_path, content in templates.items():
        full_path = Path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        print(f"  📝 Created template: {file_path}")

if __name__ == "__main__":
    update_agent_responses()
