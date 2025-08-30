"""Data models for NLP Agent"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    """Structured representation of user query intent"""
    metric_type: str = Field(..., description="Type of financial metric requested")
    time_period: str = Field(..., description="Time period for the query")
    aggregation_level: str = Field(default="monthly", description="Data aggregation level")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    comparison_periods: List[str] = Field(default_factory=list, description="Periods for comparison")
    visualization_hint: Optional[str] = Field(None, description="Suggested visualization type")
    confidence_score: float = Field(default=0.0, description="Confidence in intent extraction")


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
    """Result of NLP processing"""
    success: bool = Field(..., description="Whether processing was successful")
    query_context: Optional[QueryContext] = Field(None, description="Processed query context")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    kimi_usage: Optional[Dict[str, int]] = Field(None, description="KIMI API usage stats")