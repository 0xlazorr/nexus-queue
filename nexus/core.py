import functools
from typing import Any, Callable, Optional
from nexus.broker import RedisBroker
from nexus.models import TaskDefinition, TaskPriority
from nexus.worker import NexusWorker

class NexusTask:
    def __init__(self, app: "NexusApp", fn: Callable, name: str, priority: TaskPriority, max_retries: int):
        self.app = app
        self.fn = fn
        self.name = name
        self.priority = priority
        self.max_retries = max_retries

    async def delay(self, *args, **kwargs) -> str:
        task = TaskDefinition(
            name=self.name,
            args=list(args),
            kwargs=kwargs,
            priority=self.priority,
            max_retries=self.max_retries,
        )
        return await self.app.broker.enqueue(task)

    async def delay_until(self, delay_seconds: float, *args, **kwargs) -> str:
        import time
        task = TaskDefinition(
            name=self.name,
            args=list(args),
            kwargs=kwargs,
            priority=self.priority,
            max_retries=self.max_retries,
            execute_at=time.time() + delay_seconds,
        )
        return await self.app.broker.enqueue(task)

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

class NexusApp:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.broker = RedisBroker(redis_url)
        self.registry = {}

    def task(self, priority: str = "default", max_retries: int = 3):
        p = TaskPriority(priority)
        def decorator(fn: Callable):
            name = fn.__name__
            wrapped = NexusTask(self, fn, name, p, max_retries)
            self.registry[name] = fn
            return wrapped
        return decorator

    def create_worker(self, concurrency: int = 4) -> NexusWorker:
        return NexusWorker(broker=self.broker, concurrency=concurrency, registry=self.registry)

    async def __aenter__(self):
        await self.broker.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.broker.close()
