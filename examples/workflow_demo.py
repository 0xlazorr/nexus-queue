import asyncio
from nexus import NexusApp

app = NexusApp()

@app.task(priority="high", max_retries=2)
async def process_transaction(tx_id: str, amount_sol: float):
    print(f"💳 Executing transaction {tx_id} for {amount_sol} SOL...")
    await asyncio.sleep(0.2)
    return {"tx_id": tx_id, "status": "confirmed"}

@app.task(priority="default", max_retries=3)
async def generate_invoice(customer: str):
    print(f"📄 Rendering invoice PDF for {customer}...")
    await asyncio.sleep(0.3)
    return {"customer": customer, "status": "generated"}

async def demo():
    print("🚀 Nexus Queue End-to-End Demo...")
    async with app:
        # Enqueue high priority
        t1 = await process_transaction.delay("tx_0x99a", 4.5)
        print(f"Enqueued High-Priority Task: {t1}")

        # Enqueue default priority
        t2 = await generate_invoice.delay("Alice Corp")
        print(f"Enqueued Default Task: {t2}")

    print("Tasks safely queued into Redis.")

if __name__ == "__main__":
    asyncio.run(demo())
