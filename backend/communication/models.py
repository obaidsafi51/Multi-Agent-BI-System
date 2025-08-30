"""
Data models for communication protocols.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid


class MessageType(str, Enum):
    """Types of messages in A2A communication"""
    QUERY_PROCESSING = "query_processing"
    VISUALIZATION_REQUEST = "visualization_request"
    PERSONALIZATION_UPDATE = "personalization_update"
    DATA_REQUEST = "data_request"
    ERROR_NOTIFICATION = "error_notification"
    HEALTH_CHECK = "health_check"


class TaskStatus(str, Enum):
    """Status of ACP workflow tasks"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Types of agents in the system"""
    NLP = "nlp"
    DATA = "data"
    VISUALIZATION = "viz"
    PERSONALIZATION = "personal"
    BACKEND = "backend"


class ContextData(BaseModel):
    """Data structure for MCP context store"""
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="User session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Context data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Context expiration time")
    version: int = Field(default=1, description="Context version for conflict resolution")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentMessage(BaseModel):
    """Message structure for A2A communication"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = Field(..., description="Type of message")
    sender: AgentType = Field(..., description="Sending agent")
    recipient: AgentType = Field(..., description="Receiving agent")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    context_id: Optional[str] = Field(None, description="Associated context ID")
    correlation_id: Optional[str] = Field(None, description="Message correlation ID")
    reply_to: Optional[str] = Field(None, description="Reply queue name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ttl: Optional[int] = Field(None, description="Message TTL in seconds")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowTask(BaseModel):
    """Task structure for ACP workflow orchestration"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="Parent workflow identifier")
    task_name: str = Field(..., description="Task name/type")
    agent_type: AgentType = Field(..., description="Target agent for task")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    timeout: int = Field(default=300, description="Task timeout in seconds")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDefinition(BaseModel):
    """Workflow definition for ACP orchestration"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = Field(..., description="Workflow name")
    tasks: List[WorkflowTask] = Field(..., description="Tasks in workflow")
    context_id: Optional[str] = Field(None, description="Associated context")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthCheckResponse(BaseModel):
    """Health check response structure"""
    agent_type: AgentType = Field(..., description="Agent type")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }