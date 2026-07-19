import asyncio
import json
import time
import random
import websockets
import base64
import os

# 5KB string block mimicking heavy binary metric tables / raw telemetry dumps
RAW_BYTES: str = os.urandom(1024 * 3)
BIG_PAYLOAD_STRING: str = base64.b64encode(RAW_BYTES).decode('utf-8')
DEVICE_NUMBER: int = 20
PACKAGE_NUMBER: int = 1000
DELAY: int  = 0.01

async def run_device_simulation(device_id: int):
    uri = "ws://127.0.0.1:3000"
    async with websockets.connect(uri) as websocket:
        for i in range(PACKAGE_NUMBER + 1):
            payload = {
                "device_id": f"device_id_{device_id}",
                "temperature": round(random.uniform(18.0, 38.0), 2),
                "humidity": round(random.uniform(30.0, 80.0), 2),
                "timestamp": int(time.time_ns()),
                "status_payload": BIG_PAYLOAD_STRING
            }
            # Wrap standard JSON frame expected by NestJS WsAdapter
            frame = {"event": "telemetry", "data": payload};
            await websocket.send(json.dumps(frame))
            await asyncio.sleep(0.005)

async def main():
    print(f"Initializing {DEVICE_NUMBER} Simulated IoT System Devices...")
    print(f"Will send: {(DEVICE_NUMBER * PACKAGE_NUMBER):,} packets total.")
    print(f"Delay {DELAY} between packages")
    tasks = [run_device_simulation(i) for i in range(1, DEVICE_NUMBER + 1)]

    start_time = time.time()
    await asyncio.gather(*tasks)
    end_time = time.time()

    print("\n" + "="*50)
    print(f"Total Execution Time: {end_time - start_time:.3f} seconds")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
