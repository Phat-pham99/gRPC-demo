FROM python:3.13-slim

WORKDIR /app

# Install system dependencies if required, then python packages
RUN pip install --no-cache-dir fastapi uvicorn grpcio grpcio-tools pydantic

# Copy source and shared proto contract
COPY FastAPI-service/main.py .
COPY iot_data.proto .

# Compile protobuf stubs directly inside the container environment
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. iot_data.proto

EXPOSE 8000
EXPOSE 50051

CMD ["python", "main.py"]
