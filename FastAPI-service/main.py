import time
import asyncio
import grpc
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel, Field
import iot_data_pb2
import iot_data_pb2_grpc

app = FastAPI()
HOST: str = "0.0.0.0"
global COUNT
COUNT = 0

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., min_length=1)
    temperature: float
    humidity: float
    timestamp: int
    status_payload: str

# Simulated High-Performance DB Write Overhead
async def save_to_db(count, device_id: str, temp: float, hum: float, ts: str, payload: bytes):
    process_time: int = time.time_ns() - int(ts) #Delta time took to process this data package
    # Print statement showing the incoming decoded elements
    print(f"[DB Write] Frame #{count} | Delta time: {process_time} | Payload Bytes: {len(payload)}", flush=True)
    return count + 1

# --- PATH A: REST Endpoints ---
@app.post("/api/telemetry")
async def receive_rest(payload: TelemetryPayload):
    global COUNT
    COUNT = await save_to_db(
        COUNT,
        payload.device_id,
        payload.temperature,
        payload.humidity,
        str(payload.timestamp),
        payload.status_payload
    )
    print(f"count: {COUNT}", flush=True)
    return {"success": True, "message": "Saved via REST"}

# --- PATH B: Unary gRPC Servicer Implementation ---
class IotServiceServicer(iot_data_pb2_grpc.IotServiceServicer):
    def __init__(self):
        self.COUNT = 0
        
    async def SendTelemetry(self, request, context):
        print(request, flush=True)
        # print( request.device_id.decode('utf-8'))

        self.COUNT = await save_to_db(
            self.COUNT,
            request.device_id,
            request.temperature,
            request.humidity,
            request.timestamp,
            request.status_payload
        )
        print(f"count: {COUNT}", flush=True)
        return iot_data_pb2.TelemetryResponse(success=True, message=f"Saved via Unary gRPC. Total: {self.COUNT}")

# --- PATH C: Client-Streaming gRPC Servicer Implementation ---
class IotServiceStreamServicer(iot_data_pb2_grpc.IotServiceStreamServicer):
    def __init__(self):
        self.COUNT = 0

    async def SendTelemetry(self, request_iterator, context):
        frames_received = 0
        
        # request_iterator contains the continuous incoming HTTP/2 frames stream
        async for request in request_iterator:
            print(request)
            frames_received += 1
            self.COUNT = await save_to_db(
                self.COUNT,
                request.device_id,
                request.temperature,
                request.humidity,
                request.timestamp,
                request.status_payload
            )
        print(f"count: {COUNT}", flush=True)
        print(f"[Stream] Finished stream. Processed {frames_received} frames sequentially.", flush=True)
        
        # Return a single response back to the NestJS Gateway after stream completes
        return iot_data_pb2.TelemetryResponse(
            success=True, 
            message=f"Processed {frames_received} frames via Stream gRPC."
        )

async def run_grpc_server():
    server = grpc.aio.server()
    
    # Register both Unary and Streaming servicers to the engine instance
    iot_data_pb2_grpc.add_IotServiceServicer_to_server(IotServiceServicer(), server)
    iot_data_pb2_grpc.add_IotServiceStreamServicer_to_server(IotServiceStreamServicer(), server)
    
    server.add_insecure_port(f"{HOST}:50051")
    await server.start()
    print("[Engine] Async gRPC Server online on port 50051 (Unary & Streaming)")
    print("-----------------------------------------")
    await server.wait_for_termination()

async def main():
    config = uvicorn.Config(app, host=HOST, port=8000, log_level="warning")
    uvicorn_server = uvicorn.Server(config)
    
    print("[Engine] Starting both REST and gRPC Engines side-by-side...")
    await asyncio.gather(
        uvicorn_server.serve(),
        run_grpc_server()
    )

if __name__ == "__main__":
    asyncio.run(main())