import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { join } from 'path';
import { TelemetryGateway } from './telemetry.gateway';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'IOT_PACKAGE',
        transport: Transport.GRPC,
        options: {
          package: 'iot',
          protoPath: join(process.cwd(), './iot_data.proto'),
          url: '127.0.0.1:50051',
          loader: {
            keepCase: true,
          },
          channelOptions: {
            // Force the single connection pipe to stay alive permanently under stress
            'grpc.keepalive_time_ms': 120000,
            'grpc.keepalive_timeout_ms': 60000,
            // Increase internal timeout thresholds to give the engine queue time to breath
            'grpc.http2.min_time_between_pings_ms': 10000,
            'grpc.http2.max_pings_without_data': 0,
            // Set data caps to 10MB to avoid packet fragmentation dropping connections
            'grpc.max_receive_message_length': 1024 * 1024 * 10,
            'grpc.max_send_message_length': 1024 * 1024 * 10,
          }
        },
      },
    ]),
  ],
  providers: [TelemetryGateway],
})
export class AppModule {}
