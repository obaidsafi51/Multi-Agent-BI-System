# Task 7: Enhanced Workflow Orchestration Implementation Plan

## 📊 **Current System Analysis**

### ✅ **What's Already Excellent**

- **Sequential orchestration**: NLP → Data → Viz workflow properly implemented
- **Comprehensive error handling**: 4 error types with specific recovery actions
- **Agent health checks**: Pre-flight verification before workflow execution
- **Timeout configuration**: Tailored timeouts per agent and operation type
- **Extensive logging**: Complete workflow debugging and performance tracking
- **Response validation**: Standardized format validation for all agents
- **Fallback mechanisms**: Graceful degradation when agents fail

### ❌ **Identified Gaps**

- **No circuit breaker pattern**: Repeated failures don't trigger circuit breaking
- **Monolithic function**: Orchestration logic embedded in `process_query()`
- **Unused sophisticated orchestrator**: `ACPOrchestrator` exists but not integrated
- **Basic retry logic**: Simple fallbacks without exponential backoff
- **Limited workflow control**: No cancellation or pause/resume capabilities

## 🎯 **Enhancement Strategy**

### Phase 1: Refactor Existing Logic into WorkflowOrchestrator Class

#### 1.1 Extract Current Orchestration Logic

```python
# File: backend/workflow/orchestrator.py
class WorkflowOrchestrator:
    """Enhanced workflow orchestration with advanced patterns"""

    def __init__(self):
        self.nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://nlp-agent:8001")
        self.data_agent_url = os.getenv("DATA_AGENT_URL", "http://data-agent:8002")
        self.viz_agent_url = os.getenv("VIZ_AGENT_URL", "http://viz-agent:8003")

        # Circuit breakers for each agent
        self.circuit_breakers = {
            "nlp": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "data": CircuitBreaker(failure_threshold=3, recovery_timeout=120),
            "viz": CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        }

        # Workflow state management
        self.active_workflows = {}
        self.workflow_metrics = WorkflowMetrics()
```

#### 1.2 Move Process Query Logic

- Extract current `process_query()` logic into `orchestrator.execute_workflow()`
- Maintain all existing error handling and validation
- Keep current timeout configurations and fallback mechanisms

### Phase 2: Integrate Existing ACPOrchestrator

#### 2.1 Analyze Current ACPOrchestrator

Found in `backend/communication/acp.py`:

- ✅ Task dependency management
- ✅ Workflow state tracking
- ✅ Retry logic with configurable attempts
- ✅ Error recovery mechanisms
- ✅ Performance monitoring

#### 2.2 Integration Strategy

```python
class EnhancedWorkflowOrchestrator:
    def __init__(self):
        # Current orchestration logic
        self.basic_orchestrator = WorkflowOrchestrator()

        # Advanced orchestration for complex workflows
        self.acp_orchestrator = ACPOrchestrator()

    async def execute_workflow(self, request: QueryRequest) -> QueryResponse:
        """Route to appropriate orchestrator based on complexity"""
        if self._is_complex_workflow(request):
            return await self._execute_via_acp(request)
        else:
            return await self._execute_basic_workflow(request)
```

### Phase 3: Implement Circuit Breaker Pattern

#### 3.1 Circuit Breaker Implementation

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if service recovered

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
```

#### 3.2 Integration with Agent Communication

```python
async def send_to_nlp_agent_with_circuit_breaker(self, query: str, query_id: str) -> dict:
    """Enhanced NLP agent communication with circuit breaker"""
    try:
        return await self.circuit_breakers["nlp"].call(
            self._send_to_nlp_agent, query, query_id
        )
    except CircuitOpenError:
        logger.warning(f"NLP Agent circuit breaker OPEN - using fallback")
        return await self.fallback_nlp_processing(query, query_id)
```

### Phase 4: Add Advanced Retry Policies

#### 4.1 Exponential Backoff with Jitter

```python
import random
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryPolicy:
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60) +
             wait_random(0, 1),  # Add jitter
        reraise=True
    )
    async def execute_with_retry(func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        return await func(*args, **kwargs)
```

#### 4.2 Agent-Specific Retry Configurations

```python
RETRY_CONFIGS = {
    "nlp": {"max_attempts": 3, "base_delay": 1, "max_delay": 30},
    "data": {"max_attempts": 2, "base_delay": 2, "max_delay": 60},
    "viz": {"max_attempts": 3, "base_delay": 1, "max_delay": 30}
}
```

### Phase 5: Enhanced State Management & Observability

#### 5.1 Workflow State Persistence

```python
@dataclass
class WorkflowState:
    workflow_id: str
    status: WorkflowStatus
    current_step: str
    completed_steps: List[str]
    failed_steps: List[str]
    started_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class WorkflowStateManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def save_state(self, state: WorkflowState):
        await self.redis.setex(
            f"workflow:{state.workflow_id}",
            3600,  # 1 hour TTL
            json.dumps(state.__dict__, default=str)
        )

    async def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        data = await self.redis.get(f"workflow:{workflow_id}")
        return WorkflowState(**json.loads(data)) if data else None
```

#### 5.2 Workflow Metrics Collection

```python
class WorkflowMetrics:
    def __init__(self):
        self.total_workflows = 0
        self.successful_workflows = 0
        self.failed_workflows = 0
        self.step_metrics = defaultdict(lambda: {"count": 0, "avg_duration": 0})

    def record_workflow_completion(self, workflow_id: str, success: bool, duration_ms: int):
        self.total_workflows += 1
        if success:
            self.successful_workflows += 1
        else:
            self.failed_workflows += 1

    def record_step_completion(self, step_name: str, duration_ms: int):
        metrics = self.step_metrics[step_name]
        metrics["count"] += 1
        # Running average calculation
        metrics["avg_duration"] = (
            (metrics["avg_duration"] * (metrics["count"] - 1) + duration_ms) /
            metrics["count"]
        )
```

### Phase 6: Workflow Control Features

#### 6.1 Cancellation Support

```python
import asyncio
from contextlib import asynccontextmanager

class CancellableWorkflow:
    def __init__(self):
        self.cancellation_tokens = {}

    @asynccontextmanager
    async def cancellable_execution(self, workflow_id: str):
        """Context manager for cancellable workflow execution"""
        cancel_event = asyncio.Event()
        self.cancellation_tokens[workflow_id] = cancel_event

        try:
            yield cancel_event
        finally:
            self.cancellation_tokens.pop(workflow_id, None)

    async def cancel_workflow(self, workflow_id: str):
        """Cancel a running workflow"""
        if workflow_id in self.cancellation_tokens:
            self.cancellation_tokens[workflow_id].set()
            return True
        return False
```

## 📋 **Implementation Checklist**

### Phase 1: Foundation (Week 1)

- [ ] Create `backend/workflow/` directory structure
- [ ] Implement `WorkflowOrchestrator` class
- [ ] Extract current `process_query` logic into orchestrator
- [ ] Add comprehensive unit tests
- [ ] Update backend/main.py to use new orchestrator

### Phase 2: Circuit Breakers (Week 1-2)

- [ ] Implement `CircuitBreaker` class with states
- [ ] Add circuit breakers to all agent communications
- [ ] Configure failure thresholds per agent type
- [ ] Add circuit breaker status monitoring endpoint
- [ ] Test circuit breaker behavior under failure scenarios

### Phase 3: Advanced Retry (Week 2)

- [ ] Install and configure tenacity for retry logic
- [ ] Implement exponential backoff with jitter
- [ ] Add agent-specific retry configurations
- [ ] Test retry behavior with simulated failures
- [ ] Monitor retry metrics and tune configurations

### Phase 4: ACP Integration (Week 2-3)

- [ ] Analyze existing ACPOrchestrator capabilities
- [ ] Create integration layer between orchestrators
- [ ] Add complexity detection for workflow routing
- [ ] Implement task dependency management
- [ ] Test complex multi-step workflow scenarios

### Phase 5: State Management (Week 3)

- [ ] Implement WorkflowState persistence in Redis
- [ ] Add workflow progress tracking
- [ ] Create workflow metrics collection
- [ ] Add monitoring dashboard endpoints
- [ ] Test state recovery scenarios

### Phase 6: Control Features (Week 3-4)

- [ ] Implement workflow cancellation support
- [ ] Add pause/resume functionality (if needed)
- [ ] Create workflow management API endpoints
- [ ] Add workflow status monitoring UI
- [ ] Test cancellation and control scenarios

## 🚀 **Success Metrics**

### Performance Targets

- **Response Time**: ≤ 10% increase from current performance
- **Error Recovery**: 95% success rate on retry attempts
- **Circuit Breaker**: < 1% false positives
- **State Persistence**: 99.9% reliability

### Monitoring KPIs

- Workflow success rate by step
- Average processing time per agent
- Circuit breaker activation frequency
- Retry attempt distribution
- Failed workflow recovery rate

## 🔧 **Integration Points**

### Files to Modify

1. **backend/main.py**: Update to use WorkflowOrchestrator
2. **backend/workflow/orchestrator.py**: New orchestrator implementation
3. **backend/workflow/circuit_breaker.py**: Circuit breaker implementation
4. **backend/workflow/metrics.py**: Metrics collection
5. **requirements.txt**: Add tenacity for retry logic

### API Endpoints to Add

- `GET /api/workflow/{workflow_id}/status` - Workflow status
- `POST /api/workflow/{workflow_id}/cancel` - Cancel workflow
- `GET /api/workflow/metrics` - System workflow metrics
- `GET /api/circuit-breakers/status` - Circuit breaker states

## ⚠️ **Risk Mitigation**

### Implementation Risks

1. **Performance regression**: Extensive testing before deployment
2. **Breaking current functionality**: Feature flags for gradual rollout
3. **State persistence issues**: Backup/recovery mechanisms
4. **Circuit breaker false positives**: Careful threshold tuning

### Rollback Strategy

- Keep existing process_query as backup
- Feature flag to disable new orchestrator
- Gradual migration with monitoring
- Automated rollback triggers on error spike

---

**This enhanced approach leverages our existing robust foundation while adding the missing advanced patterns for enterprise-grade workflow orchestration.**
