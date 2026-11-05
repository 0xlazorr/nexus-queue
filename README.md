# Nexus Queue 🚀⚙️

A production-ready, distributed asynchronous task queue and job orchestration engine engineered in **Python** using **Asyncio** and **Redis**.

Designed for high-throughput distributed background processing with priority scheduling, exponential backoff retries with jitter, dead-letter queues (DLQ), and distributed worker lease coordination.

---

## 🏛️ Architecture & Core Concepts

```text
Producer (NexusApp)
      │
      ├──► Priority Queues (High / Default / Low)
      ├──► Delayed / Scheduled ZSet (Timestamp-based sorting)
      ▼
Redis Backend (Atomic Lua scripts for lease acquisition)
      ▲
      │
Distributed Workers (Asyncio concurrency semaphore)
      ├──► Success ──► Result Store & Metrics
      ├──► Failure ──► Exponential Backoff Retry (Max Retries)
      └──► Exhausted Retries ──► Dead Letter Queue (DLQ)
```

---

## 🌟 Key Highlights

- **Multi-Level Priority Queuing**: Supports `HIGH`, `DEFAULT`, and `LOW` priorities with strict starvation-free fair dispatching.
- **Delayed & Scheduled Execution**: Enqueues jobs for future execution using sorted sets (`ZADD` / `ZRANGEBYSCORE`).
- **Resilient Distributed Leases**: Prevents duplicate executions across concurrent worker nodes with atomic Redis token leases.
- **Smart Retries & Jitter**: Full exponential backoff with decorrelated jitter to prevent thundering herd spikes on downstream APIs.
- **Dead-Letter Queue (DLQ)**: Automatically captures repeatedly failing jobs for post-mortem inspection, debugging, and manual replay.
- **Live Terminal Telemetry**: Beautiful real-time CLI dashboard powered by `rich` reporting throughput, latency, and worker heartbeats.

---

## 📂 Project Structure

```text
nexus-queue/
├── pyproject.toml         # Packaging & metadata
├── requirements.txt       # Dependencies
├── nexus/
│   ├── __init__.py        # Public API exports
│   ├── models.py          # Pydantic schemas (Task, Status, Result)
│   ├── broker.py          # Redis async client & atomic Lua scripts
│   ├── worker.py          # Async worker loop, signal handling, execution
│   ├── retry.py           # Exponential backoff & jitter algorithms
│   ├── telemetry.py       # Metrics collector & telemetry exporter
│   └── cli.py             # Rich CLI management suite
├── examples/
│   └── workflow_demo.py   # Standalone demo & benchmark
└── README.md
```

---

## 🚀 Quickstart

### 1. Define & Dispatch Tasks
```python
import asyncio
from nexus import NexusApp

app = NexusApp(redis_url="redis://localhost:6379/0")

@app.task(priority="high", max_retries=3)
async def send_welcome_email(user_id: int, email: str):
    print(f"📧 Sending welcome email to {email} (User {user_id})...")
    await asyncio.sleep(0.5)
    return {"status": "sent", "user_id": user_id}

async def main():
    async with app:
        # Instant dispatch
        task_id = await send_welcome_email.delay(101, "alice@example.com")
        print(f"Dispatched task: {task_id}")

        # Delayed dispatch (run in 10 seconds)
        delayed_id = await send_welcome_email.delay_until(10, 102, "bob@example.com")
        print(f"Scheduled delayed task: {delayed_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Start Worker Daemon
```bash
nexus worker --concurrency 8 --queues high,default,low
```

### 3. Inspect Queue Telemetry
```bash
nexus status
```

---

## 📜 License
MIT License • Engineered by [Lazarus Ebi](https://github.com/0xlazorr)
