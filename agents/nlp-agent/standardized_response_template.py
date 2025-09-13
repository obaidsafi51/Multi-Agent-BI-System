"""
Template for creating standardized NLP Agent responses that comply 
with the Multi-Agent BI System workflow standards.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

# Import standardized models from local shared package
from shared.models.workflow import NLPResponse, QueryIntent, AgentMetadata, ErrorResponse

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
