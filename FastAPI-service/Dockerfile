FROM python:3.13-slim

WORKDIR /app

COPY FastAPI-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY FastAPI-service/main.py .
COPY iot_data.proto .

# Compile protobuf stubs directly inside the container environment
RUN python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. iot_data.proto

EXPOSE 8000
EXPOSE 50051

CMD ["python3", "-u", "main.py"]
