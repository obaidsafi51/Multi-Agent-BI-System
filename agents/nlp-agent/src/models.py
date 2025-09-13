"""Data models for NLP Agent

This module now imports standardized models from local shared.models
and defines only NLP-specific models not covered by shared models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Import standardized shared models from local package
from shared.models.workflow import QueryIntent, NLPResponse, AgentResponse
from shared.models.agents import AgentRequest, AgentError


class FinancialEntity(BaseModel):
    """Recognized financial terms and metrics"""
    entity_type: str = Field(..., description="Type of financial entity")
    entity_value: str = Field(..., description="Normalized entity value")
    confidence_score: float = Field(..., description="Recognition confidence")
    synonyms: List[str] = Field(default_factory=list, description="Alternative terms")
    original_text: str = Field(..., description="Original text from query")


class QueryContext(BaseModel):
    """Contextual information for query processing"""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    query_id: str = Field(..., description="Unique query identifier")
    original_query: str = Field(..., description="Original user query")
    processed_query: str = Field(..., description="Preprocessed query text")
    intent: Optional[QueryIntent] = Field(None, description="Extracted query intent")
    entities: List[FinancialEntity] = Field(default_factory=list, description="Recognized entities")
    ambiguities: List[str] = Field(default_factory=list, description="Detected ambiguities")
    clarifications: List[str] = Field(default_factory=list, description="Suggested clarifications")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context information")
    created_at: datetime = Field(default_factory=datetime.now, description="Context creation time")


class KimiRequest(BaseModel):
    """Request model for KIMI API"""
    model: str = Field(default="moonshot-v1-8k", description="KIMI model to use")
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    temperature: float = Field(default=0.1, description="Response randomness")
    max_tokens: int = Field(default=2000, description="Maximum response tokens")
    stream: bool = Field(default=False, description="Stream response")


class KimiResponse(BaseModel):
    """Response model from KIMI API"""
    id: str = Field(..., description="Response ID")
    object: str = Field(..., description="Response object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    usage: Dict[str, int] = Field(..., description="Token usage information")


class AmbiguityType(str, Enum):
    """Types of query ambiguities"""
    TIME_PERIOD = "time_period"
    METRIC_TYPE = "metric_type"
    COMPARISON_BASIS = "comparison_basis"
    AGGREGATION_LEVEL = "aggregation_level"
    ENTITY_REFERENCE = "entity_reference"


class Ambiguity(BaseModel):
    """Detected ambiguity in query"""
    ambiguity_type: AmbiguityType = Field(..., description="Type of ambiguity")
    description: str = Field(..., description="Description of the ambiguity")
    possible_interpretations: List[str] = Field(..., description="Possible interpretations")
    confidence_score: float = Field(..., description="Confidence in ambiguity detection")
    suggested_clarification: str = Field(..., description="Suggested clarification question")


class ProcessingResult(BaseModel):
    """Result of simplified NLP processing"""
    query_id: str = Field(..., description="Query identifier")
    success: bool = Field(..., description="Whether processing was successful")
    intent: Optional[QueryIntent] = Field(None, description="Extracted query intent")
    sql_query: Optional[str] = Field(None, description="Generated SQL query")
    query_context: Optional[Dict[str, Any]] = Field(None, description="Processed query context as dict")
    mcp_context_stored: bool = Field(default=False, description="Whether context was stored in MCP")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    processing_path: str = Field(default="unknown", description="Processing path taken")


class ProcessRequest(BaseModel):
    """Request model for NLP processing"""
    query: str = Field(..., description="Natural language query to process")
    query_id: str = Field(..., description="Unique query identifier")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context for query processing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me quarterly revenue for 2024",
                "query_id": "query_12345",
                "user_id": "user_123",
                "session_id": "session_456",
                "context": {
                    "source": "backend_api",
                    "timestamp": "2025-01-15T10:30:00Z"
                },
                "database_context": {
                    "database_name": "Agentic_BI",
                    "schema_version": "1.0.0",
                    "available_tables": ["financial_overview", "cash_flow"],
                    "user_preferences": {
                        "default_currency": "USD",
                        "date_format": "YYYY-MM-DD"
                    }
                }
            }
        }