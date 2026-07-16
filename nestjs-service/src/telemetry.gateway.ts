import { WebSocketGateway, SubscribeMessage, MessageBody } from '@nestjs/websockets';
import { Inject, OnModuleInit } from '@nestjs/common';
import { ClientGrpc } from '@nestjs/microservices';
import { Metadata } from '@grpc/grpc-js';
import axios from 'axios';
import { Observable, lastValueFrom } from 'rxjs';

interface TelemetryPayload {
  device_id: string;
  temperature: number;
  humidity: number;
  timestamp: number;
  status_payload: string;
}

interface gRPCTelemetryPayload {
  device_id: string;
  temperature: number;
  humidity: number;
  timestamp: number;
  status_payload: Buffer<ArrayBufferLike>;
}

interface IotService {
  sendTelemetry(data: TelemetryPayload): Observable<any>;
}

@WebSocketGateway()
export class TelemetryGateway implements OnModuleInit {
  // 1. Fixed with "!" operator to tell TS it's initialized onModuleInit
  private iotService!: IotService;
  
  // 2. Will resolve fine once @types/node is installed
  private useGrpc = process.env.MODE === 'grpc';

  constructor(@Inject('IOT_PACKAGE') private client: ClientGrpc) {}

  onModuleInit() {
    this.iotService = this.client.getService<IotService>('IotService');
    console.log(`\n>>> [Gateway] API channel loaded in [${this.useGrpc ? 'gRPC' : 'REST'}] mode. <<<\n`);
  }

  @SubscribeMessage('telemetry')
  async handleTelemetry(@MessageBody() payload: TelemetryPayload) {
    if (this.useGrpc) {
    // Convert the string into a raw binary buffer so gRPC maps it to 'bytes'
    const gRpcPayload: TelemetryPayload = {
      ...payload,
      status_payload: payload.status_payload,
    };
    try {
      const metadata = new Metadata();
      
      // Define a 60-second deadline from right now
      const deadline = new Date(Date.now() + 60000);

      // NestJS ClientGrpc allows passing Metadata as the 2nd argument.
      // To attach the deadline, we pass it inside the Options object as the 3rd argument, 
      // BUT we must cast the service interface to 'any' to satisfy the strict TS compiler hook.
      await lastValueFrom(
        this.iotService.sendTelemetry(gRpcPayload as any)
      );
      // await (this.iotService as any).sendTelemetry(payload, metadata, { deadline });
    } catch (err) {
        console.error('gRPC Pipeline Error', err);
      }
    } else {
      try {
        // Double check this URL handles 'service_b' if running in Docker containers!
        await axios.post('http://127.0.0.1:8000/api/telemetry', payload);
      } catch (err) {
        console.error('REST Pipeline Error', err);
      }
    }
  }
}