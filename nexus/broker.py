import json
import time
from typing import Optional, List, Dict
import redis.asyncio as redis
from nexus.models import TaskDefinition, TaskPriority, TaskResult, TaskStatus

class RedisBroker:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        if not self.client:
            self.client = redis.from_url(self.redis_url, decode_responses=True)

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    def _queue_key(self, priority: TaskPriority) -> str:
        return f"nexus:queue:{priority.value}"

    async def enqueue(self, task: TaskDefinition) -> str:
        await self.connect()
        data = task.model_dump_json()

        # If task is delayed
        now = time.time()
        if task.execute_at > now:
            await self.client.zadd("nexus:delayed", {data: task.execute_at})
        else:
            await self.client.lpush(self._queue_key(task.priority), data)
        return task.id

    async def fetch_next(self, priorities: List[TaskPriority]) -> Optional[TaskDefinition]:
        await self.connect()

        # 1. Promote due delayed tasks
        now = time.time()
        due_tasks = await self.client.zrangebyscore("nexus:delayed", 0, now, start=0, num=10)
        for raw in due_tasks:
            removed = await self.client.zrem("nexus:delayed", raw)
            if removed:
                task_data = json.loads(raw)
                p = TaskPriority(task_data.get("priority", "default"))
                await self.client.lpush(self._queue_key(p), raw)

        # 2. Dequeue by priority order
        for p in priorities:
            raw = await self.client.rpop(self._queue_key(p))
            if raw:
                data = json.loads(raw)
                return TaskDefinition(**data)
        return None

    async def mark_completed(self, result: TaskResult):
        await self.connect()
        key = f"nexus:result:{result.task_id}"
        await self.client.setex(key, 86400, result.model_dump_json())
        await self.client.hincrby("nexus:stats", "completed", 1)

    async def mark_dead_letter(self, task: TaskDefinition, error: str):
        await self.connect()
        data = task.model_dump()
        # Redact sensitive parameters in dead letter queue to prevent credential leaks
        if "kwargs" in data and isinstance(data["kwargs"], dict):
            sensitive_patterns = {"password", "token", "secret", "api_key", "private_key", "auth", "key"}
            data["kwargs"] = {
                k: ("[REDACTED]" if any(s in k.lower() for s in sensitive_patterns) else v)
                for k, v in data["kwargs"].items()
            }
        data["last_error"] = error
        await self.client.lpush("nexus:dlq", json.dumps(data))
        await self.client.hincrby("nexus:stats", "dead_letter", 1)

    async def get_queue_depths(self) -> Dict[str, int]:
        await self.connect()
        depths = {}
        for p in [TaskPriority.HIGH, TaskPriority.DEFAULT, TaskPriority.LOW]:
            depths[p.value] = await self.client.llen(self._queue_key(p))
        depths["delayed"] = await self.client.zcard("nexus:delayed")
        depths["dlq"] = await self.client.llen("nexus:dlq")
        return depths
