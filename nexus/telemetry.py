import time
from typing import Dict, Any
from nexus.broker import RedisBroker

class TelemetryCollector:
    def __init__(self, broker: RedisBroker):
        self.broker = broker

    async def collect_snapshot(self) -> Dict[str, Any]:
        depths = await self.broker.get_queue_depths()
        stats = {}
        if self.broker.client:
            raw_stats = await self.broker.client.hgetall("nexus:stats")
            stats = {k: int(v) for k, v in raw_stats.items()}
        return {
            "timestamp": time.time(),
            "queues": depths,
            "stats": stats,
        }
