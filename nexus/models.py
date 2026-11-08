from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid
from pydantic import BaseModel, Field

class TaskPriority(str, Enum):
    HIGH = "high"
    DEFAULT = "default"
    LOW = "low"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"

class TaskDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.DEFAULT
    status: TaskStatus = TaskStatus.PENDING
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = Field(default_factory=time.time)
    execute_at: float = Field(default_factory=time.time)
    timeout_seconds: float = 60.0

    def transition_to(self, new_status: Union[TaskStatus, str]) -> None:
        """Validates and enforces explicit finite state machine transitions for tasks."""
        target = TaskStatus(new_status)
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.RUNNING},
            TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING, TaskStatus.DEAD_LETTER},
            TaskStatus.RETRYING: {TaskStatus.PENDING},
            TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.DEAD_LETTER},
            TaskStatus.COMPLETED: set(),
            TaskStatus.DEAD_LETTER: set(),
        }
        if self.status != target and target not in valid_transitions.get(self.status, set()):
            raise ValueError(f"Illegal task transition from {self.status.value} to {target.value} for task {self.id}")
        self.status = target

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    completed_at: float = Field(default_factory=time.time)
