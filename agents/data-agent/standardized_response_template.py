"""
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
