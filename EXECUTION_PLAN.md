# EDISS Portfolio Execution Plan
## Granular Step-by-Step Implementation Guide

> **Companion to `PLAN.md`.** This file contains the exact tactical steps, file paths, commands, and code snippets required to execute each phase. Do not begin until authorized.

---

## Environment Assumptions

- OS: Linux (Ubuntu/Debian recommended for `tc` support)
- Docker & Docker Compose installed
- Python 3.13+, Node.js 20+, `kubectl`, `helm`, `terraform` available
- Working directory: repository root (`gRPC-demo/`)
- All paths in this document are relative to repository root unless stated otherwise.

---

## Phase 1 — Baseline Observability & Instrumentation
**Goal:** Instrument both services before changing anything else. Measure first.

---

### Task 1.1 — Instrument FastAPI Engine with Prometheus

**File to edit:** `FastAPI-service/main.py`
**New files:** `FastAPI-service/requirements.txt` (append dependency)

**Steps:**

1. Add `prometheus-client==0.21.1` to `FastAPI-service/requirements.txt`.
2. Update `FastAPI-service/main.py`:
   - Import:
     ```python
     from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
     from starlette.responses import Response
     ```
   - Define metrics at module level:
     ```python
     FRAMES_TOTAL = Counter(
         "telemetry_frames_total",
         "Total telemetry frames processed",
         ["transport"]
     )
     PROCESSING_DURATION = Histogram(
         "telemetry_processing_seconds",
         "Time spent processing a frame",
         ["transport"],
         buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
     )
     PAYLOAD_SIZE = Histogram(
         "telemetry_payload_bytes",
         "Payload size in bytes",
         buckets=[1024, 2048, 4096, 8192, 16384, 32768, 65536]
     )
     ```
   - Add `/metrics` endpoint:
     ```python
     @app.get("/metrics")
     async def metrics():
         return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
     ```
   - Wrap REST handler:
     ```python
     @app.post("/api/telemetry")
     async def receive_rest(payload: TelemetryPayload):
         start = time.time()
         global COUNT
         COUNT = await save_to_db(...)
         PROCESSING_DURATION.labels(transport="rest").observe(time.time() - start)
         FRAMES_TOTAL.labels(transport="rest").inc()
         PAYLOAD_SIZE.observe(len(payload.status_payload))
         return {"success": True, "message": "Saved via REST"}
     ```
   - Wrap gRPC unary handler:
     ```python
     async def SendTelemetry(self, request, context):
         start = time.time()
         self.COUNT = await save_to_db(...)
         PROCESSING_DURATION.labels(transport="grpc_unary").observe(time.time() - start)
         FRAMES_TOTAL.labels(transport="grpc_unary").inc()
         PAYLOAD_SIZE.observe(len(request.status_payload))
         return iot_data_pb2.TelemetryResponse(...)
     ```
   - Wrap gRPC stream handler:
     ```python
     async def SendTelemetry(self, request_iterator, context):
         async for request in request_iterator:
             start = time.time()
             self.COUNT = await save_to_db(...)
             PROCESSING_DURATION.labels(transport="grpc_stream").observe(time.time() - start)
             FRAMES_TOTAL.labels(transport="grpc_stream").inc()
             PAYLOAD_SIZE.observe(len(request.status_payload))
         return iot_data_pb2.TelemetryResponse(...)
     ```
3. Verify: run `docker compose up --build -d`, then `curl http://localhost:8000/metrics` should show metrics lines.

---

### Task 1.2 — Instrument NestJS Gateway with Prometheus

**File to edit:** `nestjs-service/src/telemetry.gateway.ts`
**New files:** `nestjs-service/src/metrics.provider.ts`, update `nestjs-service/package.json`

**Steps:**

1. Add `prom-client` to `nestjs-service/package.json` dependencies, then run `npm install prom-client`.
2. Create `nestjs-service/src/metrics.provider.ts`:
   ```typescript
   import { register, Counter, Histogram, Gauge } from 'prom-client';

   export const webSocketConnections = new Gauge({
     name: 'gateway_ws_connections_active',
     help: 'Active WebSocket connections',
   });

   export const egressFramesTotal = new Counter({
     name: 'gateway_egress_frames_total',
     help: 'Total frames forwarded to engine',
     labelNames: ['transport'],
   });

   export const gatewayLatency = new Histogram({
     name: 'gateway_forward_latency_seconds',
     help: 'Latency forwarding a frame to engine',
     labelNames: ['transport'],
     buckets: [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
   });

   export function getMetrics(): string {
     return register.metrics();
   }
   ```
3. Update `nestjs-service/src/telemetry.gateway.ts`:
   - Import metrics provider.
   - Increment `webSocketConnections` on some lifecycle hook (or count active ws clients if possible; otherwise increment/decrement per connection event if adapter exposes it).
   - In `handleTelemetry`, wrap the forward path:
     ```typescript
     const start = Date.now();
     if (this.useGrpc) {
       this.IotServiceStream$.next(gRpcPayload);
     } else {
       await axios.post(...);
     }
     gatewayLatency.labels(this.useGrpc ? 'grpc' : 'rest').observe((Date.now() - start) / 1000);
     egressFramesTotal.labels(this.useGrpc ? 'grpc' : 'rest').inc();
     ```
4. Add a `/metrics` HTTP endpoint in NestJS. Since NestJS has no HTTP controller yet:
   - Create `nestjs-service/src/app.controller.ts` with a `@Controller()` route for `/metrics` that returns `getMetrics()`.
   - Ensure `AppModule` declares `AppController`.
5. Expose port `3001` in `docker-compose.yaml` for the metrics endpoint if using a separate port; otherwise keep on `3000`.

---

### Task 1.3 — OpenTelemetry Auto-Instrumentation

**New files:** `FastAPI-service/otel_config.py`, `nestjs-service/src/tracing.module.ts`, update Dockerfiles.

**Steps:**

1. **FastAPI OTel:**
   - Add to `FastAPI-service/requirements.txt`:
     ```
     opentelemetry-api==1.29.0
     opentelemetry-sdk==1.29.0
     opentelemetry-instrumentation-fastapi==0.50b0
     opentelemetry-exporter-otlp==1.29.0
     ```
   - Create `FastAPI-service/otel_config.py`:
     ```python
     from opentelemetry import trace
     from opentelemetry.sdk.trace import TracerProvider
     from opentelemetry.sdk.trace.export import BatchSpanProcessor
     from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
     from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

     def setup_tracing(app):
         provider = TracerProvider()
         processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True))
         provider.add_span_processor(processor)
         trace.set_tracer_provider(provider)
         FastAPIInstrumentor.instrument_app(app)
     ```
   - Call `setup_tracing(app)` in `main.py` before `uvicorn` starts.

2. **NestJS OTel:**
   - Add packages:
     ```bash
     npm install @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/auto-instrumentations-node @opentelemetry/exporter-trace-otlp-grpc
     ```
   - Create `nestjs-service/src/tracing.ts`:
     ```typescript
     import { NodeSDK } from '@opentelemetry/sdk-node';
     import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
     import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';

     const sdk = new NodeSDK({
       traceExporter: new OTLPTraceExporter({ url: 'http://otel-collector:4317' }),
       instrumentations: [getNodeAutoInstrumentations()],
     });

     sdk.start();
     ```
   - Import `./tracing` at the top of `nestjs-service/src/main.ts` (before any other imports).
3. Verify traces appear in OTLP collector logs.

---

### Task 1.4 — Deploy Observability Stack via Docker Compose

**New files:** `docker-compose.observability.yaml` or extend existing `docker-compose.yaml`.

**Steps:**

1. Add services to `docker-compose.yaml`:
   - **Prometheus**:
     ```yaml
     prometheus:
       image: prom/prometheus:v3.1.0
       volumes:
         - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
       ports:
         - "9090:9090"
     ```
   - **Grafana**:
     ```yaml
     grafana:
       image: grafana/grafana:11.4.0
       volumes:
         - ./observability/grafana/provisioning:/etc/grafana/provisioning
         - ./observability/dashboards:/var/lib/grafana/dashboards
       ports:
         - "3001:3000"
     ```
   - **OTel Collector**:
     ```yaml
     otel-collector:
       image: otel/opentelemetry-collector:0.116.1
       volumes:
         - ./observability/otel-collector-config.yml:/etc/otelcol/config.yaml
       ports:
         - "4317:4317"   # OTLP gRPC
         - "4318:4318"   # OTLP HTTP
     ```
2. Create directories and files:
   - `observability/prometheus.yml` — scrape configs for `fastapi_service:8000`, `nestjs_service:3000` (or `3001`), `otel-collector:8889`.
   - `observability/otel-collector-config.yml` — receivers OTLP, exporters Prometheus + Jaeger, service pipeline traces + metrics.
   - `observability/grafana/provisioning/datasources/datasource.yml` — auto-provision Prometheus + Jaeger.
   - `observability/dashboards/telemetry-benchmark.json` — starter dashboard JSON.
3. Run `docker compose up --build -d` and verify:
   - `curl localhost:9090/api/v1/targets` shows UP.
   - Grafana at `localhost:3001` has Prometheus datasource.
   - Jaeger UI at `localhost:16686` shows traces.

---

### Task 1.5 — Structured JSON Logs

**Steps:**

1. **FastAPI:** Replace all `print()` with a structured logger:
   ```python
   import logging, json
   logger = logging.getLogger("telemetry-engine")
   logger.setLevel(logging.INFO)
   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter(json.dumps({"timestamp":"%(asctime)s","level":"%(levelname)s","service":"engine","message":"%(message)s"})))
   ```
   Simpler approach: use `python-json-logger` package and configure it.

2. **NestJS:** Use `nestjs-pino` or a custom interceptor to log in JSON with trace IDs.

3. Ensure all log lines include `trace_id` when available.

---

## Phase 2 — Benchmark Harness & Reproducible Data Collection

---

### Task 2.1 — Refactor Simulator into Benchmark Harness

**File to create/replace:** `benchmark.py` (replaces `iot_simulation.py` or keeps both)

**Steps:**

1. Design CLI with `argparse`:
   ```bash
   python benchmark.py --mode grpc --devices 20 --frames 1000 --delay 0.005 --payload-bytes 3072 --warmup-frames 100 --output-dir ./results
   ```
2. Architecture of `benchmark.py`:
   - `main()` parses args.
   - `BenchmarkRunner` class:
     - `__init__` stores config.
     - `generate_payload(seed)` returns deterministic Base64 payload.
     - `run_warmup()` sends warmup frames, discards metrics.
     - `run_benchmark()` sends main frames, records per-frame send latency (optional).
     - `run_cooldown()` optional sleep.
3. Keep WebSocket event format identical: `{"event":"telemetry","data":...}`.

---

### Task 2.2 — Warm-up / Cool-down Periods

**Steps:**
1. Add `--warmup-frames` arg (default 100).
2. Send warmup frames before starting the timer; discard any engine/metrics data from this window.
3. After main frames, sleep 2s (cooldown) to allow final buffers to flush before querying Prometheus.

---

### Task 2.3 — Deterministic Random Seeding

**Steps:**
1. `random.seed(config.seed)` at harness start.
2. `os.urandom` is not seedable; instead use `random.randbytes(payload_bytes)` seeded.
3. Document that `--seed` ensures reproducible payloads.

---

### Task 2.4 — Automated Prometheus Scrape & Report Generation

**Steps:**
1. After benchmark run, query Prometheus HTTP API:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, telemetry_processing_seconds)'
   ```
2. Build a `ResultCollector` class with methods:
   - `query_prometheus(query, start, end)`
   - `collect_latency_percentiles()` → p50, p95, p99
   - `collect_throughput()` → `rate(telemetry_frames_total[1m])`
   - `collect_error_rate()`
   - `collect_resource_usage()` → from container metrics if available
3. Write JSON report:
   ```json
   {
     "run_id": "2025-01-15T10-30-00",
     "mode": "grpc",
     "config": { ... },
     "results": {
       "latency": {"p50": 0.0012, "p95": 0.0034, "p99": 0.0051},
       "throughput": 1850.4,
       "total_frames": 20020,
       "duration_seconds": 12.4
     }
   }
   ```
4. Generate Markdown report `results/YYYY-MM-DD_HH-MM-{mode}.md` with embedded table.

---

### Task 2.5 — Resource Monitoring

**Steps:**
1. Option A: Enable cAdvisor in Docker Compose, scrape with Prometheus.
2. Option B: Parse `docker stats` output during benchmark with a background thread.
3. Add CPU seconds and memory bytes to result JSON.

---

### Task 2.6 — Comparison Script

**File to create:** `compare_results.py`

**Steps:**
1. CLI: `python compare_results.py results/2025-01-15T10-30-grpc.json results/2025-01-15T10-35-rest.json`
2. Read both JSONs, compute deltas:
   - Latency delta: ((rest - grpc) / rest) * 100
   - Throughput delta
   - Error rate delta
3. Output `comparison.md` with Markdown table.

---

## Phase 3 — Distributed Topology & Cloud-Native Deployment

---

### Task 3.1 — Kubernetes Plain Manifests

**Directory:** `k8s/`

**Files to create:**
- `k8s/namespace-region-a.yaml` — `region-a`
- `k8s/namespace-region-b.yaml` — `region-b`
- `k8s/fastapi-deployment.yaml` — Deployment + Service in `region-b`
- `k8s/nestjs-deployment.yaml` — Deployment + Service in `region-a`
- `k8s/configmap.yaml` — `MODE`, `REST_API_URL`, `GRPC_API_URL`

**Steps:**
1. Write Deployment specs with container ports:
   - FastAPI: `8000` (REST), `50051` (gRPC)
   - NestJS: `3000` (WS), `3001` (metrics if separate)
2. Write Service specs (ClusterIP) for internal DNS:
   - `fastapi-service.region-b.svc.cluster.local`
3. Test locally with `kind create cluster`, then `kubectl apply -f k8s/`.

---

### Task 3.2 — Helm Chart

**Directory:** `helm/telemetry-benchmark/`

**Files:** `Chart.yaml`, `values.yaml`, `templates/` (deployment, service, configmap, ingress if needed)

**Steps:**
1. Create chart scaffold:
   ```bash
   helm create helm/telemetry-benchmark
   ```
2. Customize `values.yaml`:
   ```yaml
   replicaCount: 1
   mode: grpc
   resources:
     requests:
       cpu: 100m
       memory: 256Mi
   networkChaos:
     enabled: true
     latency: "50ms"
     jitter: "10ms"
     loss: "0.1%"
   ```
3. Parameterize `templates/nestjs-deployment.yaml` to inject `MODE` and `networkChaos` sidecar.
4. Deploy:
   ```bash
   helm install benchmark ./helm/telemetry-benchmark --set mode=grpc
   ```

---

### Task 3.3 — Multi-Namespace Local K8s (kind)

**Steps:**
1. Ensure `kind` is installed.
2. Create cluster:
   ```bash
   kind create cluster --name telemetry
   ```
3. Load Docker images into kind (or use image registry):
   ```bash
   kind load docker-image fastapi_service:latest --name telemetry
   kind load docker-image nestjs_service:latest --name telemetry
   ```
4. Apply manifests or Helm chart.
5. Verify cross-namespace communication:
   ```bash
   kubectl run -n region-a debug --rm -i --tty --image=busybox -- wget -qO- http://fastapi-service.region-b.svc.cluster.local:8000/docs
   ```

---

### Task 3.4 — Network Emulation via `tc` Sidecar

**Steps:**
1. Create a small init/sidecar container image using `alpine` + `iproute2`:
   ```dockerfile
   FROM alpine:3.21
   RUN apk add --no-cache iproute2
   COPY entrypoint.sh /entrypoint.sh
   ENTRYPOINT ["/entrypoint.sh"]
   ```
   Entrypoint script (`entrypoint.sh`):
   ```sh
   #!/bin/sh
   TARGET_IP=$(getent hosts fastapi-service.region-b.svc.cluster.local | awk '{ print $1 }')
   tc qdisc add dev eth0 root netem delay ${LATENCY} ${JITTER} loss ${LOSS}
   ```
2. Add this as an initContainer in NestJS Deployment with `NET_ADMIN` capability.
3. Verify delay is active:
   ```bash
   kubectl exec -n region-a deploy/nestjs-gateway -- ping -c 5 fastapi-service.region-b
   ```

---

### Task 3.5 — Health Checks & Probes

**Steps:**
1. **FastAPI:** Add a `/health` endpoint in `main.py`:
   ```python
   @app.get("/health")
   async def health():
       return {"status": "ok"}
   ```
2. **gRPC Health:** Use `grpcio-health-checking` package, add `HealthServicer` to gRPC server.
3. Update K8s manifests:
   - FastAPI Deployment:
     ```yaml
     livenessProbe:
       httpGet:
         path: /health
         port: 8000
       initialDelaySeconds: 5
       periodSeconds: 10
     readinessProbe:
       httpGet:
         path: /health
         port: 8000
       initialDelaySeconds: 2
       periodSeconds: 5
     ```
   - NestJS Deployment:
     - HTTP liveness on `/metrics` or `/health`.
     - Readiness on `/health`.

---

### Task 3.6 — Docker Compose Local Chaos (Optional)

**Steps:**
1. Add a `tc-sidecar` service in Docker Compose with `network_mode: service:nestjs_service` and `cap_add: [NET_ADMIN]`.
2. Provide `docker-compose.chaos.yaml` override file.

---

### Task 3.7 — Terraform Project Initialization

**Directory:** `terraform/`

**Files to create:**
- `terraform/main.tf` — providers and backend config
- `terraform/variables.tf` — input variables (region, cluster name, node type, etc.)
- `terraform/outputs.tf` — cluster endpoint, kubeconfig command
- `terraform/backend.tf` — remote state config (S3 + DynamoDB for locking, or local for demo)
- `terraform/modules/vpc/` — VPC, subnets, NAT gateway, route tables
- `terraform/modules/eks/` — EKS cluster, managed node groups, IAM roles
- `terraform/modules/ecr/` — container registries for FastAPI and NestJS images
- `terraform/helm_releases.tf` — Helm provider deploying the telemetry-benchmark chart

**Steps:**

1. **Provider & Backend:**
   ```hcl
   terraform {
     required_providers {
       aws = { source = "hashicorp/aws", version = "~> 5.0" }
       helm = { source = "hashicorp/helm", version = "~> 2.0" }
     }
     backend "s3" {
       bucket         = "telemetry-benchmark-tfstate"
       key            = "env/prod/terraform.tfstate"
       region         = "us-east-1"
       encrypt        = true
       dynamodb_table = "terraform-locks"
     }
   }
   ```
   For local-only demo, use `backend "local" {}` in `backend.tf`.

2. **VPC Module:**
   - Create a VPC (~256 addresses, `10.0.0.0/16`).
   - 2 public subnets + 2 private subnets across AZs.
   - NAT Gateway in public subnet for private egress.
   - Security group: allow ingress 3000 (WS), 8000 (REST), 50051 (gRPC), 9090 (Prometheus), 3001 (Grafana) from VPC CIDR only.

3. **EKS Module:**
   - EKS cluster (`terraform-aws-modules/eks/aws`) with managed node group.
   - Node instance: `t3.medium` minimum (2 vCPU, 4 GB) for demo; `t3.large` recommended.
   - IAM roles: cluster role, node role, IRSA role for LoadBalancer Controller if using ALB.
   - Enable cluster logging (control plane) to CloudWatch.

4. **ECR Module:**
   - Two ECR repos: `telemetry-fastapi` and `telemetry-nestjs`.
   - Lifecycle policy: retain last 5 images.

5. **Helm Release:**
   ```hcl
   provider "helm" {
     kubernetes {
       host                   = module.eks.cluster_endpoint
       cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
       token                  = data.aws_eks_cluster_auth.this.token
     }
   }

   resource "helm_release" "telemetry_benchmark" {
     name       = "telemetry-benchmark"
     chart      = "${path.module}/../helm/telemetry-benchmark"
     namespace  = "default"
     values     = [file("${path.module}/values-prod.yaml")]
   }
   ```

6. **Initialize & Validate:**
   ```bash
   cd terraform
   terraform init
   terraform validate
   terraform plan -out=tfplan
   ```

---

### Task 3.8 — Terraform Helm Provider Integration

**Steps:**
1. Ensure the Helm provider authenticates to the EKS cluster using the kubeconfig generated by the EKS module.
2. Create environment-specific value files:
   - `terraform/values-prod.yaml` — overrides for EKS (resource limits, replicaCount=2, node selectors).
   - `terraform/values-dev.yaml` — minimal resources for cost control.
3. Add `depends_on` from `helm_release` to `module.eks` so Terraform creates the cluster before attempting Helm deployment.
4. After `terraform apply`, verify:
   ```bash
   aws eks update-kubeconfig --region us-east-1 --name telemetry-cluster
   kubectl get pods -n region-a
   kubectl get pods -n region-b
   ```

---

### Task 3.9 — Remote State & Secret Management

**Steps:**
1. **Sensitive variables:** Store in `terraform/terraform.tfvars` (gitignored). Example:
   ```hcl
   aws_region       = "us-east-1"
   cluster_name     = "telemetry-cluster"
   node_instance_type = "t3.medium"
   ```
2. **Never commit `.tfstate` or `.tfvars`:** Add to `.gitignore`:
   ```
   terraform/*.tfvars
   terraform/*.tfstate
   terraform/*.tfstate.*
   terraform/.terraform/
   ```
3. **Cost guardrails:** Add a `budget.tf` optional module or document expected AWS costs (~$0.10/hour for t3.medium EKS demo).
4. **Destroy capability:** Document `terraform destroy` in `INFRASTRUCTURE.md` so the full stack can be torn down cleanly.

---

## Phase 4 — Chaos Engineering & Resilience Testing

---

### Task 4.1 — Circuit Breaker on REST Path

**File:** `nestjs-service/src/telemetry.gateway.ts`

**Steps:**
1. Install `opossum`:
   ```bash
   npm install opossum
   ```
2. Instantiate a breaker for REST calls:
   ```typescript
   import CircuitBreaker from 'opossum';

   const axiosPost = (url: string, data: any) => axios.post(url, data);
   const breaker = new CircuitBreaker(axiosPost, {
     timeout: 3000,
     errorThresholdPercentage: 50,
     resetTimeout: 30000,
   });

   breaker.on('open', () => console.error('Circuit breaker OPEN'));
   breaker.on('halfOpen', () => console.warn('Circuit breaker HALF-OPEN'));
   breaker.on('close', () => console.log('Circuit breaker CLOSED'));
   ```
3. Replace `axios.post` with `breaker.fire(...)`.
4. Emit a custom metric counter `gateway_circuit_breaker_state_total{state="open"}` when state changes.

---

### Task 4.2 — Retries with Exponential Backoff

**Steps:**
1. Either configure `axios-retry` or implement simple backoff in the REST catch block.
2. For gRPC: document existing keepalive options in `app.module.ts`; add `grpc.service_config` JSON if needed for retries.

---

### Task 4.3 — Benchmark Matrix

**Steps:**
1. Create a runner script `run_chaos_matrix.py`:
   ```python
   scenarios = [
       {"name": "baseline", "latency": "0ms", "loss": "0%", "bandwidth": ""},
       {"name": "lat_50ms", "latency": "50ms", "loss": "0%", "bandwidth": ""},
       {"name": "loss_1pct", "latency": "0ms", "loss": "1%", "bandwidth": ""},
       {"name": "lat_50ms_loss_1pct", "latency": "50ms", "loss": "1%", "bandwidth": ""},
       {"name": "bw_1mbps", "latency": "0ms", "loss": "0%", "bandwidth": "1mbit"},
   ]
   modes = ["grpc", "rest"]
   for mode in modes:
       for scenario in scenarios:
           set_chaos(scenario)
           run_benchmark(mode)
           collect_results()
   ```
2. Store all results in `results/matrix/`.

---

### Task 4.4 — Degradation Analysis Document

**File:** `DEGRADATION_ANALYSIS.md`

**Steps:**
1. After matrix completes, programmatically find the packet loss threshold where REST error rate > gRPC error rate.
2. Document in Markdown with embedded tables and conclusions.

---

### Task 4.5 — Graceful Degradation

**Steps:**
1. In NestJS gateway `handleTelemetry`, if forward fails (catch block), increment `gateway_dropped_frames_total` metric and log structured warning.
2. Optionally maintain a small ring buffer (10s) for retry-on-reconnect; for EDISS scope, dropping with metric is sufficient.

---

## Phase 5 — Intelligent Systems Layer

---

### Task 5.1 — Anomaly Detection Service

**Directory:** `anomaly-service/`

**Files:** `main.py`, `model.py`, `requirements.txt`, `Dockerfile`

**Steps:**
1. Create a lightweight FastAPI service with an endpoint `/detect`.
2. Accept a batch of telemetry frames `{device_id, temperature, humidity, timestamp}`.
3. Maintain a per-device rolling window (last N frames) in memory or simple dict.
4. Fit an `IsolationForest` on the window when it reaches size N.
5. Return `is_anomaly: bool` + `score`.
6. The Telemetry Engine can POST to this service asynchronously (fire-and-forget or background task).

---

### Task 5.2 — Sliding-Window Anomaly Detector

**Steps:**
1. Implement `AnomalyDetector` class in `model.py`:
   ```python
   from sklearn.ensemble import IsolationForest
   import numpy as np

   class AnomalyDetector:
       def __init__(self, window_size=50, contamination=0.05):
           self.window = []
           self.window_size = window_size
           self.contamination = contamination

       def fit_predict(self, temp, hum):
           self.window.append([temp, hum])
           if len(self.window) > self.window_size:
               self.window.pop(0)
           if len(self.window) < 10:
               return False, 0.0
           clf = IsolationForest(contamination=self.contamination, random_state=42)
           clf.fit(self.window)
           score = clf.decision_function([[temp, hum]])[0]
           pred = clf.predict([[temp, hum]])[0]
           return pred == -1, score
   ```
2. Expose via FastAPI endpoint.

---

### Task 5.3 — Edge Filter Rule Engine

**Steps:**
1. In NestJS gateway, add a simple rule check before forwarding:
   ```typescript
   if (payload.temperature > 50.0) {
       console.warn(JSON.stringify({event: "edge_alert", device_id: payload.device_id, reason: "temp_threshold", value: payload.temperature}));
   }
   ```
2. Increment metric `gateway_edge_alerts_total{rule="temp_threshold"}`.
3. Document that edge alerts have ~0ms added latency vs cloud inference which adds network RTT.

---

### Task 5.4 — Anomaly Metrics

**Steps:**
1. FastAPI engine emits `anomaly_detected_total{device_id, rule_type}` when result from anomaly service returns positive.
2. Add panel in Grafana dashboard.

---

### Task 5.5 — Intelligence Architecture Document

**File:** `INTELLIGENCE.md`

**Steps:**
1. Document pipeline: raw telemetry → edge filter (simple rules, <1ms) → cloud inference (IsolationForest, ~50ms) → alert.
2. Justify separation: edge for latency-critical alerts; cloud for complex pattern detection.
3. Cite relevant EDISS themes (intelligent systems, runtime decision-making).

---

## Phase 6 — Academic Packaging & Portfolio Finalization

---

### Task 6.1 — Research Methodology Document

**File:** `RESEARCH.md`

**Structure:**
- **Research Question:** Does gRPC client-streaming exhibit measurably lower latency and higher throughput than REST POST under emulated IoT telemetry load and degraded network conditions?
- **Hypothesis:** gRPC will outperform REST by ≥20% in p99 latency under latency ≥50ms and packet loss ≥1%.
- **Independent Variables:** Transport mode (grpc, rest), network latency, packet loss, bandwidth.
- **Dependent Variables:** p50/p95/p99 processing latency, throughput (frames/sec), CPU usage, memory usage, error rate.
- **Methodology:** Controlled benchmark with warm-up, deterministic load, automated Prometheus collection, 5 replications per condition.
- **Threats to Validity:** Single-host emulation (use K8s to mitigate), absence of real hardware IoT devices (justified by simulator parity), limited payload diversity.

---

### Task 6.2 — Result Graphs

**Steps:**
1. Write a Python script `render_charts.py` using `matplotlib`:
   - Bar chart: p50/p95/p99 latency by mode.
   - Line chart: throughput vs latency under increasing network latency.
   - Heatmap: error rate matrix (mode × loss %).
2. Save PNGs to `assets/`.
3. Embed into `RESULTS.md`.

---

### Task 6.3 — README Refactor

**Steps:**
1. Rewrite `README.md` opening to frame as a benchmarking experiment, not a demo.
2. Add badges for technologies.
3. Include architecture diagram, quickstart, and “How to Reproduce” section.
4. Link to `RESEARCH.md`, `RESULTS.md`, `PLAN.md`, `EXECUTION_PLAN.md`.

---

### Task 6.4 — Reproducible Builds

**Steps:**
1. Pin base images in Dockerfiles to digests (or specific semver tags).
2. Lock dependencies: `requirements.txt` already pinned; `package-lock.json` already present.
3. Add `docker-bake.hcl` or a `Makefile` target `make build`.

---

### Task 6.5 — Makefile / Taskfile

**File:** `Makefile`

**Targets:**
```makefile
.PHONY: dev benchmark chaos k8s-deploy tf-plan tf-apply tf-destroy clean

dev:
	docker compose up --build -d

benchmark:
	python benchmark.py --mode grpc --output-dir ./results
	python benchmark.py --mode rest --output-dir ./results
	python compare_results.py ./results/*grpc.json ./results/*rest.json

chaos:
	python run_chaos_matrix.py

k8s-deploy:
	kind create cluster --name telemetry || true
	kind load docker-image fastapi_service:latest nestjs_service:latest --name telemetry
	kubectl apply -f k8s/

tf-plan:
	cd terraform && terraform init && terraform plan -out=tfplan

tf-apply:
	cd terraform && terraform apply tfplan

tf-destroy:
	cd terraform && terraform destroy

clean:
	docker compose down -v
	kind delete cluster --name telemetry || true
```

---

### Task 6.6 — Final Code Review

**Checklist:**
- [ ] No `console.log` noise; all logs are structured.
- [ ] No hardcoded URLs in source; all via env vars / ConfigMap.
- [ ] No secrets in git.
- [ ] `node_modules`, `__pycache__`, `.pyc` ignored.
- [ ] Consistent formatting (Prettier for TS, Black for Python).
- [ ] Inline comments on architectural decisions (circuit breaker, `tc`, keepalive).

---

### Task 6.7 — Git History

**Steps:**
1. Commit per phase:
   - `feat(observability): add Prometheus, OTel, Grafana stack`
   - `feat(benchmark): deterministic harness with warm-up and report generation`
   - `feat(k8s): multi-namespace deployment with Helm and network emulation`
   - `feat(terraform): AWS VPC, EKS, IAM, ECR, and Helm provider deployment`
   - `feat(chaos): circuit breaker, retry matrix, degradation analysis`
   - `feat(intelligence): anomaly detection service and edge filter`
   - `docs: academic framing, README, RESEARCH.md, RESULTS.md, INFRASTRUCTURE.md`
2. Optionally create branches per phase and merge via PR for clean history.

---

## Immediate Next Step

**Phase 1, Task 1.1:** Instrument `FastAPI-service/main.py` with Prometheus metrics (`prometheus-client`) and expose `/metrics`.

Awaiting your mark to proceed.
