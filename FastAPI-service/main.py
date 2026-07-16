import asyncio
import grpc
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel, Field
import iot_data_pb2
import iot_data_pb2_grpc

app = FastAPI()
global COUNT
COUNT = 0
class TelemetryPayload(BaseModel):
    device_id: str = Field(..., min_length=1)
    temperature: float
    humidity: float
    timestamp: int
    status_payload: str

# Simulated High-Performance DB Write Overhead
async def save_to_db(count, device_id: str, temp: float, hum: float, ts: int, payload: str):
    now = datetime.now()
    # await asyncio.sleep(0.001)  # 1ms database transaction simulation
    # print(
    #     f"device_id->{device_id} | payload->{payload}",
    #     end="\r",
    #     flush=True
    #     )
    # print(f"Now: {now}", end="\r", flush=True)
    print(f"count: {count}", end="\r", flush=True)
    return count+1

# --- PATH A: REST Endpoints ---
@app.post("/api/telemetry")
async def receive_rest(payload: TelemetryPayload):
    global COUNT
    COUNT = await save_to_db(
        COUNT,
        payload.device_id,
        payload.temperature,
        payload.humidity,
        payload.timestamp,
        payload.status_payload
    )
    print(f"count: {COUNT}", end="\r", flush=True)
    return {"success": True, "message": "Saved via REST"}

# --- PATH B: gRPC Servicer Implementation ---
class IotServiceServicer(iot_data_pb2_grpc.IotServiceServicer):
    def __init__(self):
        self.COUNT = 0
    async def SendTelemetry(self, request, context):
        self.COUNT = await save_to_db(
            self.COUNT,
            request.device_id,
            request.temperature,
            request.humidity,
            request.timestamp,
            request.status_payload
        )
        return iot_data_pb2.TelemetryResponse(success=True, message="Saved via gRPC")

async def run_grpc_server():
    server = grpc.aio.server()
    iot_data_pb2_grpc.add_IotServiceServicer_to_server(IotServiceServicer(), server)
    server.add_insecure_port("127.0.0.1:50051")
    await server.start()
    print("[Engine] Async gRPC Server online on port 50051")
    print("-----------------------------------------")
    await server.wait_for_termination()

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    uvicorn_server = uvicorn.Server(config)
    
    print("[Engine] Starting both REST and gRPC Engines side-by-side...")
    await asyncio.gather(
        uvicorn_server.serve(),
        run_grpc_server()
    )

if __name__ == "__main__":
    asyncio.run(main())