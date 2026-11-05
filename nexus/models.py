from enum import Enum
from typing import Any, Dict, List, Optional
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
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = Field(default_factory=time.time)
    execute_at: float = Field(default_factory=time.time)
    timeout_seconds: float = 60.0

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    completed_at: float = Field(default_factory=time.time)
