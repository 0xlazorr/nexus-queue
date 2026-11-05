import argparse
import asyncio
from rich.console import Console
from rich.table import Table
from nexus.broker import RedisBroker
from nexus.telemetry import TelemetryCollector

console = Console()

async def show_status(redis_url: str):
    broker = RedisBroker(redis_url)
    collector = TelemetryCollector(broker)
    data = await collector.collect_snapshot()

    table = Table(title="⚡ Nexus Queue Telemetry Dashboard")
    table.add_column("Queue / Stream", style="cyan", no_wrap=True)
    table.add_column("Depth (Messages)", style="magenta")

    for q, depth in data["queues"].items():
        table.add_row(q.capitalize(), str(depth))

    console.print(table)
    await broker.close()

def main():
    parser = argparse.ArgumentParser(description="Nexus Task Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command")

    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.add_argument("--redis", default="redis://localhost:6379/0")

    args = parser.parse_args()
    if args.command == "status":
        asyncio.run(show_status(args.redis))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
