"""
ACP (Agent Communication Protocol) implementation using Celery.

Provides workflow orchestration with task queues and error handling.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import asyncio
from celery import Celery, Task
from celery.exceptions import Retry, WorkerLostError
from kombu import Queue

from .models import WorkflowTask, WorkflowDefinition, TaskStatus, AgentType
from .mcp import MCPContextStore
from .a2a import A2AMessageBroker


logger = logging.getLogger(__name__)


class ACPOrchestrator:
    """Celery-based workflow orchestrator for ACP protocol"""
    
    def __init__(self, broker_url: str = "redis://localhost:6379/1", 
                 backend_url: str = "redis://localhost:6379/2",
                 mcp_store: Optional[MCPContextStore] = None,
                 a2a_broker: Optional[A2AMessageBroker] = None):
        """
        Initialize ACP orchestrator.
        
        Args:
            broker_url: Celery broker URL
            backend_url: Celery result backend URL
            mcp_store: MCP context store instance
            a2a_broker: A2A message broker instance
        """
        self.broker_url = broker_url
        self.backend_url = backend_url
        self.mcp_store = mcp_store
        self.a2a_broker = a2a_broker
        
        # Initialize Celery app
        self.celery_app = Celery(
            'acp_orchestrator',
            broker=broker_url,
            backend=backend_url,
            include=['backend.communication.acp']
        )
        
        # Configure Celery
        self.celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=300,  # 5 minutes
            task_soft_time_limit=240,  # 4 minutes
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_disable_rate_limits=False,
            task_default_retry_delay=60,  # 1 minute
            task_max_retries=3,
            task_routes={
                'acp.execute_workflow': {'queue': 'workflow'},
                'acp.execute_task': {'queue': 'tasks'},
                'acp.health_check': {'queue': 'health'}
            },
            task_queues=(
                Queue('workflow', routing_key='workflow'),
                Queue('tasks', routing_key='tasks'),
                Queue('health', routing_key='health'),
            )
        )
        
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._task_handlers: Dict[str, Callable] = {}
        
        # Register Celery tasks
        self._register_celery_tasks()
    
    def _register_celery_tasks(self) -> None:
        """Register Celery tasks"""
        
        @self.celery_app.task(bind=True, name='acp.execute_workflow')
        def execute_workflow_task(self, workflow_id: str) -> Dict[str, Any]:
            """Execute workflow task"""
            return asyncio.run(self._execute_workflow_async(workflow_id))
        
        @self.celery_app.task(bind=True, name='acp.execute_task')
        def execute_task_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute individual task"""
            task = WorkflowTask(**task_data)
            return asyncio.run(self._execute_task_async(task))
        
        @self.celery_app.task(bind=True, name='acp.health_check')
        def health_check_task(self) -> Dict[str, Any]:
            """Health check task"""
            return asyncio.run(self._health_check_async())
        
        self.execute_workflow_task = execute_workflow_task
        self.execute_task_task = execute_task_task
        self.health_check_task = health_check_task
    
    def register_task_handler(self, task_name: str, handler: Callable) -> None:
        """
        Register task handler.
        
        Args:
            task_name: Name of the task
            handler: Async function to handle the task
        """
        self._task_handlers[task_name] = handler
        logger.debug(f"Registered handler for task: {task_name}")
    
    async def create_workflow(self, workflow_name: str, tasks: List[WorkflowTask], 
                            context_id: Optional[str] = None) -> WorkflowDefinition:
        """
        Create a new workflow.
        
        Args:
            workflow_name: Name of the workflow
            tasks: List of tasks in the workflow
            context_id: Associated context ID
            
        Returns:
            Created workflow definition
        """
        workflow = WorkflowDefinition(
            workflow_name=workflow_name,
            tasks=tasks,
            context_id=context_id
        )
        
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"Created workflow {workflow.workflow_id}: {workflow_name}")
        
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> str:
        """
        Execute workflow asynchronously.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Celery task ID
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Submit workflow execution task
        task = self.execute_workflow_task.delay(workflow_id)
        logger.info(f"Submitted workflow {workflow_id} for execution: {task.id}")
        
        return task.id
    
    async def _execute_workflow_async(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute workflow implementation.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow execution result
        """
        try:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            workflow.status = TaskStatus.RUNNING
            logger.info(f"Starting workflow execution: {workflow.workflow_name}")
            
            # Build dependency graph
            task_dependencies = self._build_dependency_graph(workflow.tasks)
            
            # Execute tasks in dependency order
            completed_tasks = set()
            failed_tasks = set()
            
            while len(completed_tasks) + len(failed_tasks) < len(workflow.tasks):
                # Find tasks ready to execute
                ready_tasks = []
                for task in workflow.tasks:
                    if (task.task_id not in completed_tasks and 
                        task.task_id not in failed_tasks and
                        all(dep in completed_tasks for dep in task.dependencies)):
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    # Check if we're stuck due to failed dependencies
                    remaining_tasks = [t for t in workflow.tasks 
                                     if t.task_id not in completed_tasks and t.task_id not in failed_tasks]
                    if remaining_tasks:
                        logger.error(f"Workflow {workflow_id} stuck - no ready tasks")
                        workflow.status = TaskStatus.FAILURE
                        break
                    else:
                        break
                
                # Execute ready tasks in parallel
                task_futures = []
                for task in ready_tasks:
                    future = self.execute_task_task.delay(task.dict())
                    task_futures.append((task, future))
                
                # Wait for task completion
                for task, future in task_futures:
                    try:
                        result = future.get(timeout=task.timeout)
                        if result.get('status') == TaskStatus.SUCCESS:
                            completed_tasks.add(task.task_id)
                            task.status = TaskStatus.SUCCESS
                            task.result = result.get('result')
                            task.completed_at = datetime.utcnow()
                        else:
                            failed_tasks.add(task.task_id)
                            task.status = TaskStatus.FAILURE
                            task.error = result.get('error')
                            task.completed_at = datetime.utcnow()
                    except Exception as e:
                        failed_tasks.add(task.task_id)
                        task.status = TaskStatus.FAILURE
                        task.error = str(e)
                        task.completed_at = datetime.utcnow()
                        logger.error(f"Task {task.task_id} failed: {e}")
            
            # Determine workflow status
            if failed_tasks:
                workflow.status = TaskStatus.FAILURE
                logger.error(f"Workflow {workflow_id} failed with {len(failed_tasks)} failed tasks")
            else:
                workflow.status = TaskStatus.SUCCESS
                logger.info(f"Workflow {workflow_id} completed successfully")
            
            return {
                'workflow_id': workflow_id,
                'status': workflow.status,
                'completed_tasks': len(completed_tasks),
                'failed_tasks': len(failed_tasks),
                'total_tasks': len(workflow.tasks)
            }
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} execution failed: {e}")
            if workflow_id in self._workflows:
                self._workflows[workflow_id].status = TaskStatus.FAILURE
            return {
                'workflow_id': workflow_id,
                'status': TaskStatus.FAILURE,
                'error': str(e)
            }
    
    async def _execute_task_async(self, task: WorkflowTask) -> Dict[str, Any]:
        """
        Execute individual task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
        """
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            logger.info(f"Executing task {task.task_id}: {task.task_name}")
            
            # Get task handler
            handler = self._task_handlers.get(task.task_name)
            if not handler:
                raise ValueError(f"No handler registered for task: {task.task_name}")
            
            # Execute task with timeout
            try:
                result = await asyncio.wait_for(
                    handler(task),
                    timeout=task.timeout
                )
                
                task.status = TaskStatus.SUCCESS
                task.result = result
                task.completed_at = datetime.utcnow()
                
                logger.info(f"Task {task.task_id} completed successfully")
                
                return {
                    'task_id': task.task_id,
                    'status': TaskStatus.SUCCESS,
                    'result': result
                }
                
            except asyncio.TimeoutError:
                raise Exception(f"Task {task.task_id} timed out after {task.timeout} seconds")
            
        except Exception as e:
            task.status = TaskStatus.FAILURE
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRY
                logger.warning(f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries}): {e}")
                
                # Schedule retry
                retry_delay = min(60 * (2 ** task.retry_count), 300)  # Exponential backoff, max 5 minutes
                retry_task = self.execute_task_task.apply_async(
                    args=[task.dict()],
                    countdown=retry_delay
                )
                
                return {
                    'task_id': task.task_id,
                    'status': TaskStatus.RETRY,
                    'retry_task_id': retry_task.id,
                    'retry_count': task.retry_count
                }
            else:
                logger.error(f"Task {task.task_id} failed after {task.max_retries} retries: {e}")
                
                return {
                    'task_id': task.task_id,
                    'status': TaskStatus.FAILURE,
                    'error': str(e)
                }
    
    def _build_dependency_graph(self, tasks: List[WorkflowTask]) -> Dict[str, List[str]]:
        """
        Build task dependency graph.
        
        Args:
            tasks: List of workflow tasks
            
        Returns:
            Dictionary mapping task IDs to their dependencies
        """
        graph = {}
        for task in tasks:
            graph[task.task_id] = task.dependencies.copy()
        
        return graph
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow status information
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        task_statuses = {}
        for task in workflow.tasks:
            task_statuses[task.task_id] = {
                'name': task.task_name,
                'status': task.status,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error': task.error,
                'retry_count': task.retry_count
            }
        
        return {
            'workflow_id': workflow_id,
            'workflow_name': workflow.workflow_name,
            'status': workflow.status,
            'created_at': workflow.created_at.isoformat(),
            'task_count': len(workflow.tasks),
            'tasks': task_statuses
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel workflow execution.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if cancelled successfully
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        try:
            # Cancel running tasks
            for task in workflow.tasks:
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()
            
            workflow.status = TaskStatus.CANCELLED
            logger.info(f"Cancelled workflow {workflow_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False
    
    async def _health_check_async(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check result
        """
        try:
            # Check Celery worker status
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            active_tasks = inspect.active()
            
            return {
                'status': 'healthy',
                'celery_workers': len(stats) if stats else 0,
                'active_workflows': len([w for w in self._workflows.values() if w.status == TaskStatus.RUNNING]),
                'total_workflows': len(self._workflows),
                'active_tasks': sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0,
                'registered_handlers': len(self._task_handlers)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get orchestrator metrics.
        
        Returns:
            Dictionary with metrics
        """
        try:
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            
            workflow_statuses = {}
            for status in TaskStatus:
                workflow_statuses[status.value] = len([
                    w for w in self._workflows.values() if w.status == status
                ])
            
            return {
                'celery_workers': len(stats) if stats else 0,
                'workflow_statuses': workflow_statuses,
                'total_workflows': len(self._workflows),
                'registered_handlers': len(self._task_handlers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {'error': str(e)}