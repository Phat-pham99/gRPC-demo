import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { WsAdapter } from '@nestjs/platform-ws';

async function bootstrap() {
  // 1. Create the application instance normally
  const app = await NestFactory.create(AppModule);
  
  // 2. Fetch the underlying native HTTP server instance explicitly 
  // and pass it into the WsAdapter so it can bind to the 'upgrade' hook immediately
  app.useWebSocketAdapter(new WsAdapter(app.getHttpServer()));
  
  // 3. Start listening on your desired gateway port
  await app.listen(3000);
  console.log('\n>>> Gateway successfully listening on Port 3000 <<<');
}
bootstrap();