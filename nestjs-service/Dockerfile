# --- Build Stage ---
FROM node:26-alpine AS builder
WORKDIR /usr/src/app

COPY package.json ./

COPY . .
# Pull the shared proto file from the root context
COPY iot_data.proto ./iot_data.proto
RUN npm install
RUN npm run build

# --- Production Stage ---
FROM node:26-alpine
WORKDIR /usr/src/app

COPY package.json ./nestjs-service/

COPY --from=builder /usr/src/app/dist ./dist
COPY --from=builder /usr/src/app/node_modules ./node_modules
COPY ../iot_data.proto ./nestjs-service/iot_data.proto

EXPOSE 3000
CMD ["node", "nestjs-service/dist/main"]
