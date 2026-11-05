import asyncio
import signal
import time
from typing import Callable, Dict, List, Optional
from nexus.broker import RedisBroker
from nexus.models import TaskDefinition, TaskPriority, TaskResult, TaskStatus
from nexus.retry import calculate_backoff

class NexusWorker:
    def __init__(
        self,
        broker: RedisBroker,
        concurrency: int = 4,
        priorities: Optional[List[TaskPriority]] = None,
        registry: Optional[Dict[str, Callable]] = None,
    ):
        self.broker = broker
        self.concurrency = concurrency
        self.priorities = priorities or [TaskPriority.HIGH, TaskPriority.DEFAULT, TaskPriority.LOW]
        self.registry = registry or {}
        self.semaphore = asyncio.Semaphore(concurrency)
        self.running = False
        self._tasks: set[asyncio.Task] = set()

    def register(self, name: str, fn: Callable):
        self.registry[name] = fn

    async def start(self):
        self.running = True
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                pass  # Windows support

        print(f"🚀 NexusWorker started (concurrency={self.concurrency}, queues={[p.value for p in self.priorities]})")

        while self.running:
            await self.semaphore.acquire()
            task = await self.broker.fetch_next(self.priorities)
            if not task:
                self.semaphore.release()
                await asyncio.sleep(0.1)
                continue

            t = asyncio.create_task(self._execute_wrapper(task))
            self._tasks.add(t)
            t.add_done_callback(self._tasks.discard)

    async def _execute_wrapper(self, task: TaskDefinition):
        try:
            fn = self.registry.get(task.name)
            if not fn:
                raise ValueError(f"Task '{task.name}' not registered on worker")

            start_t = time.time()
            if asyncio.iscoroutinefunction(fn):
                res = await asyncio.wait_for(fn(*task.args, **task.kwargs), timeout=task.timeout_seconds)
            else:
                res = fn(*task.args, **task.kwargs)

            elapsed = time.time() - start_t
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=res,
                execution_time_seconds=elapsed,
            )
            await self.broker.mark_completed(result)
            print(f"✅ [{task.id[:8]}] {task.name} completed in {elapsed:.3f}s")

        except Exception as exc:
            print(f"⚠️ [{task.id[:8]}] {task.name} failed: {exc}")
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                delay = calculate_backoff(task.retry_count)
                task.execute_at = time.time() + delay
                print(f"🔄 Retrying [{task.id[:8]}] attempt {task.retry_count}/{task.max_retries} in {delay:.1f}s")
                await self.broker.enqueue(task)
            else:
                print(f"💀 Exhausted retries for [{task.id[:8]}]. Moving to Dead Letter Queue.")
                await self.broker.mark_dead_letter(task, str(exc))
        finally:
            self.semaphore.release()

    async def stop(self):
        print("
🛑 Gracefully shutting down worker...")
        self.running = False
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.broker.close()
        print("👋 Worker stopped cleanly.")
