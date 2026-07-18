import { WebSocketGateway, SubscribeMessage, MessageBody } from '@nestjs/websockets';
import { Inject, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { ClientGrpc } from '@nestjs/microservices';
import axios from 'axios';
import { Observable, Subject } from 'rxjs';

interface TelemetryPayload {
  device_id: string;
  temperature: number;
  humidity: number;
  timestamp: number | string;
  status_payload: string; // Incoming WebSocket payload delivers this as a string
}

interface gRPCTelemetryPayload {
  device_id: string;
  temperature: number;
  humidity: number;
  timestamp: string;
  status_payload: string; // Changed to Buffer to fulfill proto 'bytes' requirement
}

interface TelemetryResponse {
  success: boolean;
  message: string;
}

// Updated to target the streaming service definition
interface IotServiceStream {
  SendTelemetry(data: Observable<gRPCTelemetryPayload>): Observable<TelemetryResponse>;
}

@WebSocketGateway()
export class TelemetryGateway implements OnModuleInit, OnModuleDestroy {
  private iotServiceStream!: IotServiceStream;
  private useGrpc = process.env.MODE === 'grpc';
  private Restful_URL: string = process.env.REST_API_URL || "http://127.0.0.1:8000";

  // The bridge between WebSocket events and the gRPC client stream
  private IotServiceStream$ = new Subject<gRPCTelemetryPayload>();

  constructor(@Inject('IOT_PACKAGE') private client: ClientGrpc) {}

  onModuleInit() {
    if (this.useGrpc) {
      try {
      this.iotServiceStream = this.client.getService<IotServiceStream>('IotServiceStream');

      // Initialize and subscribe to the long-lived gRPC stream connection
      this.iotServiceStream.SendTelemetry(this.IotServiceStream$.asObservable()).subscribe({
        next: (response) => console.log('gRPC Stream Response:', response),
        error: (err) => console.error('gRPC Stream Error:', err),
        complete: () => console.log('gRPC Stream Connection ended.'),
      });
    console.log(`\n>>> [Gateway] API channel loaded in [${this.useGrpc ? 'gRPC Stream' : 'REST'}] mode. <<<\n`);
    } catch (e) {
      console.error(e)
    } finally {
      console.log("Bruh")
    }
  }}

  @SubscribeMessage('telemetry')
  async handleTelemetry(@MessageBody() payload: TelemetryPayload) {
    if (this.useGrpc) {
      try {
        // Map incoming WS payload to match the gRPC .proto expected data types
        const gRpcPayload: gRPCTelemetryPayload = {
          device_id: String(payload.device_id),
          temperature: payload.temperature,
          humidity: payload.humidity,
          timestamp: String(payload.timestamp),
          status_payload: String(payload.status_payload),
        };

        // Push data onto the active gRPC connection stream
        this.IotServiceStream$.next(gRpcPayload);
      } catch (err) {
        console.error('Failed to stream data point via gRPC pipeline:', err);
      }
    } else {
      try {
        await axios.post(this.Restful_URL + "/api/telemetry", payload);
      } catch (err) {
        console.error('REST Pipeline Error', err);
      }
    }
  }

  // Gracefully clean up the connection stream when the gateway tears down
  onModuleDestroy() {
    if (this.IotServiceStream$) {
      this.IotServiceStream$.complete();
    }
  }
}