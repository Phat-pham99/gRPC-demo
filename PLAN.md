# EDISS Portfolio Refactor Plan
## Distributed gRPC Telemetry Benchmark for Erasmus Mundus EDISS Application

**Candidate Profile:** Senior Backend Developer at FPT Software  
**Target Program:** Erasmus Mundus Joint Master Degree — EDISS  
**Program Focus:** Engineering of Data-Intensive Intelligent Software Systems  
**Portfolio Goal:** Transform an existing gRPC vs REST IoT telemetry demo into a rigorous, distributed, cloud-native benchmarking project that demonstrates readiness for advanced study in software engineering for intelligent systems.

---

## 1. Purpose of the Refactor

The current repository demonstrates gRPC and REST communication using Docker Compose on a local machine. While this is useful as a functional demo, it does not fully represent the behavior of real distributed microservice systems.

For an EDISS Erasmus Mundus application, the project should evolve into a more academically and technically convincing system that demonstrates:

1. **Distributed systems engineering**
2. **Cloud-native deployment**
3. **Data-intensive telemetry pipelines**
4. **Runtime observability and measurement**
5. **Performance benchmarking under realistic network conditions**
6. **Intelligent systems readiness**
7. **Software architecture and DevOps maturity**

The refactored project should no longer be presented merely as a “gRPC demo”. It should be positioned as:

> A distributed, observable benchmarking framework for evaluating transport-layer efficiency in data-intensive IoT telemetry pipelines, with implications for intelligent edge-cloud systems.

This framing aligns strongly with EDISS.

---

## 2. EDISS Alignment

EDISS focuses on the engineering of modern software systems that are:

- Data-intensive
- Distributed
- Cloud-native
- Observable
- Intelligent
- Capable of supporting runtime decision-making
- Built with strong software engineering principles

The refactored project maps directly to these themes.

### EDISS Theme Mapping

| EDISS Theme | How This Project Aligns |
|---|---|
| Data-intensive software systems | The system ingests thousands of IoT telemetry frames with measurable payload size, throughput, and latency. |
| Distributed systems | Services are deployed across separate nodes, potentially across multiple AWS regions. |
| Cloud-native engineering | The system uses Kubernetes, containers, Helm, ConfigMaps, Services, and infrastructure as code. |
| Intelligent systems readiness | The telemetry pipeline can serve as the data foundation for anomaly detection, predictive monitoring, or edge intelligence. |
| Runtime observability | OpenTelemetry, Prometheus, and Grafana are used to collect and analyze system behavior. |
| Data-driven assessment | Benchmark results are based on measured latency, throughput, resource usage, and network behavior. |
| Software quality and reliability | Chaos engineering and network emulation test system behavior under degraded conditions. |
| Industrial relevance | The project reflects real IoT, edge gateway, and cloud backend architecture patterns. |

---

## 3. Current Project Limitations

The existing Docker Compose-based setup has several limitations for an EDISS portfolio:

### 3.1 Local Network Illusion

Docker Compose on localhost creates near-zero network latency. This hides the real advantages of gRPC, especially:

- HTTP/2 multiplexing
- Connection reuse
- Header compression
- Binary serialization efficiency
- Stream-based communication under latency

### 3.2 Shared Host Resources

All services run on the same machine and compete for CPU, memory, and I/O. This makes benchmarking less convincing.

### 3.3 Limited Observability

The current system relies mostly on logs and counters. EDISS values data-driven runtime assessment, so the project needs structured metrics, traces, and dashboards.

### 3.4 No Real Distributed Failure Conditions

Real systems face:

- Network latency
- Packet loss
- Jitter
- Regional distance
- Service restarts
- Resource constraints
- Connection instability

The refactored project should simulate or measure these conditions.

### 3.5 Weak Academic Framing

The project should be presented not only as working code, but as an experiment with:

- Research question
- Hypothesis
- Methodology
- Metrics
- Results
- Conclusion

---

## 4. Target Architecture

The target architecture should simulate a realistic edge-to-cloud IoT telemetry system.

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        IoT Simulator                         │
│            (Python, asyncio, benchmark harness)              │
│                     WebSocket / JSON                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────────┐
│                      Edge Gateway                            │
│                   NestJS Service                             │
│  WebSocket termination → Protocol Bridge (gRPC/REST)         │
│  Resilience: circuit breaker, health checks, retries         │
│                    Region A Namespace                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ gRPC client-stream OR REST POST
                       │ (Emulated WAN: latency, loss, jitter)
                       v
┌─────────────────────────────────────────────────────────────┐
│                   Core Telemetry Engine                      │
│                    FastAPI Service                           │
│  REST /api/telemetry, gRPC Unary/Stream, Health              │
│  Metrics: Prometheus counters, histograms, OTel traces       │
│                    Region B Namespace                        │
└──────────────┬─────────────────────────────┬────────────────┘
               │                             │
               v                             v
┌─────────────────────────┐        ┌──────────────────────────┐
│ Observability Stack      │        │   Intelligent Layer      │
│ Prometheus + Grafana     │        │ Anomaly Detection Service│
│ OpenTelemetry Collector  │        │ (Python / scikit-learn)  │
│ Jaeger / Zipkin traces   │        │ Rule Engine / Edge Filter│
└─────────────────────────┘        └──────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Infrastructure Layer (Terraform)                             │
│ AWS Provider: VPC, EKS Cluster, IAM Roles, Security Groups   │
│ Helm Provider: Deploy telemetry-benchmark chart onto EKS     │
│ Remote State: S3 backend with DynamoDB locking               │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Technology | Role |
|---|---|---|
| IoT Simulator | Python, asyncio, websockets | Configurable load generator with warm-up, cool-down, and result export |
| Edge Gateway | NestJS, `@nestjs/microservices`, `@nestjs/websockets` | WebSocket termination, protocol routing, client-streaming gRPC, resilience patterns |
| Telemetry Engine | FastAPI, `grpcio`, `uvicorn` | Dual-mode ingestion (REST + gRPC), metrics emission, simulated persistence with latency tracking |
| Observability | Prometheus, Grafana, OpenTelemetry Collector, Jaeger | Metrics aggregation, trace correlation, dashboards |
| Chaos Injection | `tc` (Linux traffic control), `pumba`, or Chaos Mesh | Network latency, jitter, packet loss, bandwidth limits between GW and Engine |
| Intelligent Layer | Python, FastAPI / Quart, scikit-learn / PyTorch (optional) | Real-time anomaly detection on telemetry windows, edge filtering rules |
| Orchestration | Kubernetes (kind/k3s), Helm charts, ConfigMaps | Cloud-native deployment, namespace isolation, resource limits |
| Infrastructure | Terraform, AWS provider, Helm provider | Infrastructure-as-Code for VPC, EKS, IAM, security groups, and Helm releases |

---

## 5. Technology Choices & Rationale

- **Prometheus + Grafana**: Industry standard for metrics. Prometheus histograms are ideal for latency percentile aggregation (p50, p95, p99).
- **OpenTelemetry**: Provides distributed tracing across WebSocket → NestJS → gRPC/REST → FastAPI, demonstrating observability maturity.
- **Kubernetes (kind/k3s)**: Local/cloud-agnostic Kubernetes distribution for portable cloud-native demonstrations.
- **tc / Pumba**: Lightweight, no external SaaS dependency. Keeps the repo fully reproducible on any Linux host.
- **Circuit Breaker (opossum)**: Shows resilience engineering — a critical skill for distributed systems portfolios.
- **scikit-learn (IsolationForest)**: Lightweight, no GPU dependency, sufficient for demonstrating intelligent systems readiness on streaming data.
- **Terraform**: Declarative infrastructure-as-code for AWS provisioning (VPC, EKS, IAM, security groups). Using Terraform with the Helm provider allows the application layer and infrastructure layer to be versioned, reviewed, and destroyed as a single unit. This demonstrates DevOps maturity and cloud-native engineering beyond Kubernetes YAML alone.

---

## 6. Execution Plan

The refactor is organized into six phases. Each phase builds upon the previous one. The final deliverable is a reproducible, observable, academically framed benchmarking system.

> **Do not begin execution until explicitly authorized.**

### Phase 1 — Baseline Observability & Instrumentation
**Goal:** Make the system measurable before changing deployment topology.

| # | Task | Deliverable |
|---|---|---|
| 1.1 | Add `prometheus-client` metrics to FastAPI: request duration histogram (`telemetry_processing_seconds`), throughput counter (`telemetry_frames_total`), payload size histogram, transport mode label. | Instrumented FastAPI engine |
| 1.2 | Add `prom-client` metrics to NestJS: WebSocket connection gauge, gateway latency histogram, frames egress counter, transport mode label. | Instrumented NestJS gateway |
| 1.3 | Add OpenTelemetry auto-instrumentation to both services and configure OTLP export to a collector. | Cross-service trace IDs visible in Jaeger/Zipkin |
| 1.4 | Deploy Prometheus, Grafana, and OpenTelemetry Collector as Docker Compose services. Provide datasource provisioning and a starter dashboard JSON. | `docker compose up` yields a working observability stack with pre-built dashboards |
| 1.5 | Standardize logs to JSON format with structured fields (`service`, `trace_id`, `span_id`, `device_id`, `delta_ns`). | Log correlation via trace IDs |

**Success Criteria:**
- A single `docker compose up` spins up all services + observability stack.
- Grafana dashboard shows live throughput, latency histograms, and connection counts.
- A trace from simulator → gateway → engine is visible end-to-end.

### Phase 2 — Benchmark Harness & Reproducible Data Collection
**Goal:** Transform the simulator from a script into a rigorous benchmark harness that produces comparable datasets.

| # | Task | Deliverable |
|---|---|---|
| 2.1 | Refactor `iot_simulation.py` into a configuration-driven benchmark harness (`benchmark.py`) with CLI arguments: `--mode={grpc,rest}`, `--devices`, `--frames`, `--delay`, `--payload-bytes`, `--warmup-frames`, `--output-dir`. | Standalone benchmark runner |
| 2.2 | Implement warm-up and cool-down periods. Discard warm-up data from final statistics. | Unbiased latency measurements |
| 2.3 | Add deterministic random seeding for repeatable payload generation. | Reproducible runs |
| 2.4 | After each run, query Prometheus HTTP API to pull aggregated metrics (p50/p95/p99 latency, throughput, error rate, CPU/memory from cAdvisor if available) and emit a JSON + Markdown report. | `results/YYYY-MM-DD_HH-MM-{mode}.json` and `.md` |
| 2.5 | Integrate resource monitoring using `docker stats` parsing or cAdvisor container metrics in Prometheus. | Per-run resource profiles |
| 2.6 | Create a benchmark comparison script that reads two result JSON files and generates a delta report (Markdown table + significance notes). | `compare_results.py` |

**Success Criteria:**
- Running the harness in `grpc` mode and `rest` mode produces two result files.
- Comparison report clearly highlights latency percentiles, throughput delta, and resource cost delta.
- Results are deterministic within ±2% when re-run with the same seed.

### Phase 3 — Distributed Topology & Cloud-Native Deployment
**Goal:** Move off single-host Docker Compose and demonstrate real network separation and cloud-native patterns.

| # | Task | Deliverable |
|---|---|---|
| 3.1 | Write Kubernetes manifests (Deployment, Service, ConfigMap, Namespace) for FastAPI engine and NestJS gateway. | `k8s/` directory with plain YAML |
| 3.2 | Create a Helm chart that parameterizes `replicaCount`, `mode` (grpc/rest), `resources.requests/limits`, and `networkLatencyMs`. | `helm/telemetry-benchmark/` |
| 3.3 | Deploy to a local Kubernetes cluster (kind or k3s) with two namespaces (`region-a` for gateway, `region-b` for engine) to simulate multi-region topology. | Working local cluster with cross-namespace service calls |
| 3.4 | Introduce network emulation between gateway and engine: use an init container or sidecar with `tc qdisc` to add configurable latency, jitter, and packet loss on the egress interface. | `values.yaml` field `networkChaos: {latency: "50ms", jitter: "10ms", loss: "0.1%"}` |
| 3.5 | Add gRPC health checks (`grpc-health-probe` or built-in health servicer) and Kubernetes liveness/readiness probes for both services. | Resilient pod lifecycle management |
| 3.6 | Update Docker Compose to optionally use `network_mode: bridge` with `tc` injected via a privileged sidecar for local chaos testing without Kubernetes. | Local chaos capability |
| 3.7 | Initialize a Terraform project (`terraform/`) with modules for AWS VPC, EKS cluster, IAM roles, security groups, and ECR repositories. | `terraform/` directory with modular, reusable IaC |
| 3.8 | Use Terraform Helm provider to deploy the `telemetry-benchmark` Helm chart onto the provisioned EKS cluster. Define `helm_release` resources with environment-specific `values.yaml` overrides. | `terraform/helm_releases.tf` applying the chart automatically after cluster creation |
| 3.9 | Configure Terraform remote state backend (local or S3 with locking) and sensitive variable management via `.tfvars` files excluded from git. | Reproducible, safe infrastructure lifecycle (plan/apply/destroy) |

**Success Criteria:**
- Services run in separate namespaces and communicate over cluster DNS.
- Adding 50ms latency between gateway and engine measurably increases end-to-end latency in Grafana.
- Pods restart correctly on failure; health probes pass under normal load.

### Phase 4 — Chaos Engineering & Resilience Testing
**Goal:** Demonstrate understanding of failure modes and defensive patterns in distributed systems.

| # | Task | Deliverable |
|---|---|---|
| 4.1 | Integrate a circuit breaker (`opossum` for NestJS) on the REST client path with configurable thresholds (failure %, timeout, reset). | Circuit breaker telemetry visible in logs/metrics |
| 4.2 | Add retries with exponential backoff and jitter for REST calls; gRPC channel options already include keepalive — document and tune them. | Resilient transport clients |
| 4.3 | Run benchmark matrix: `{grpc, rest} × {no chaos, 50ms latency, 1% packet loss, 50ms+1% loss, bandwidth 1Mbps}` and collect results. | 10 result files + comparison matrix |
| 4.4 | Measure and log degradation curves: at what packet loss % does REST error rate exceed gRPC error rate? Document in a markdown analysis. | `DEGRADATION_ANALYSIS.md` |
| 4.5 | Add graceful degradation: if the engine is unreachable, the gateway buffers frames briefly or drops them with a structured log / metric increment rather than crashing. | Graceful failure behavior |

**Success Criteria:**
- Under 1% packet loss, gRPC stream throughput degrades more gracefully than REST.
- Circuit breaker opens and closes correctly; metrics show state transitions.
- Degradation analysis document contains data-backed conclusions.

### Phase 5 — Intelligent Systems Layer (Edge Intelligence)
**Goal:** Add a lightweight intelligent component that uses the telemetry stream, demonstrating data-to-decision pipeline capability.

| # | Task | Deliverable |
|---|---|---|
| 5.1 | Add an Anomaly Detection Service (Python / FastAPI) that subscribes to a Kafka-like topic or receives frames via HTTP posts from the engine for post-processing. | `anomaly-service/` container |
| 5.2 | Implement a sliding-window anomaly detector using scikit-learn `IsolationForest` or robust z-score on temperature/humidity streams. | Trained model artifact + inference endpoint |
| 5.3 | Add an “edge filter” rule engine inside the NestJS gateway: if temperature exceeds a threshold, flag the frame locally before forwarding. | Edge-rule latency vs cloud-inference latency comparison |
| 5.4 | Emit anomaly metrics (`anomaly_detected_total`) to Prometheus with labels for `{device_id, rule_type}`. | Anomaly dashboard panel |
| 5.5 | Document the intelligent pipeline architecture and the rationale for edge-vs-cloud inference in an `INTELLIGENCE.md`. | Academic framing of ML ops decisions |

**Success Criteria:**
- Anomalies are detected in real-time with <100ms inference latency.
- Grafana shows anomaly rate per device and per rule type.
- Intelligence document explains why edge filtering is used for latency-critical alerts and cloud inference for complex patterns.

### Phase 6 — Academic Packaging & Portfolio Finalization
**Goal:** Transform the repository into a concise, convincing portfolio piece.

| # | Task | Deliverable |
|---|---|---|
| 6.1 | Write a concise `RESEARCH.md` containing: research question, hypothesis, independent/dependent variables, methodology, instrumentation, and threats to validity. | Academic methodology document |
| 6.2 | Generate benchmark result graphs using Matplotlib or Grafana rendered PNGs, embedded into a final `RESULTS.md`. | Visual evidence of performance differences |
| 6.3 | Refactor `README.md` to lead with the academic framing, architecture, and how to reproduce the benchmark. Elevate tone from “demo” to “experiment”. | Professional portfolio README |
| 6.4 | Ensure all container builds are reproducible: pin base image digests, lock dependency files, include `docker-bake.hcl` or Makefile targets. | One-command reproducibility |
| 6.5 | Add a `Makefile` or `Taskfile` with targets: `make dev`, `make benchmark`, `make chaos`, `make k8s-deploy`, `make tf-plan`, `make tf-apply`, `make clean`. | Ergonomic project commands |
| 6.6 | Document Terraform usage in `INFRASTRUCTURE.md`: architecture decisions, remote state, cost estimate, and how to provision/destroy the full AWS stack. | Infrastructure-as-Code documentation |
| 6.7 | Final code review: remove dead code, add inline comments where architecture decisions matter, ensure consistent formatting. | Clean, auditable codebase |
| 6.8 | Commit each phase with descriptive messages; ensure `main` branch history tells a clear story. | Clean git history |

**Success Criteria:**
- A reviewer can clone the repo and run `make benchmark` to reproduce the core experiment in under 10 minutes.
- README + RESEARCH.md + RESULTS.md + INFRASTRUCTURE.md together read as a mini research paper.
- Terraform plan/apply creates a working AWS EKS cluster and deploys the benchmark system automatically.
- No TODO comments, no hardcoded secrets, no node_modules in git.

---

## 7. Definition of Done

The refactor is complete when:

1. The system can be deployed on Kubernetes (local or cloud) with Helm.
2. Terraform provisions the full AWS cloud infrastructure (VPC, EKS, IAM, security groups) and deploys the application via the Helm provider.
3. Benchmarks are fully automated, reproducible, and export latency percentiles + resource usage.
4. Observability stack provides live dashboards and distributed traces.
5. Chaos engineering tests demonstrate quantified resilience differences between gRPC and REST.
6. An intelligent layer adds real-time inference and edge filtering.
7. All documentation frames the project as a rigorous experiment aligned with EDISS themes.

---

## 8. Risk & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Kubernetes overhead exceeds local machine capacity | High | Use `kind` or `k3s` with resource limits; keep replica count to 1 per service for demo |
| OpenTelemetry instrumentation adds latency noise | Medium | Use asynchronous batch exporters with small batch sizes; validate baseline vs instrumented delta |
| Anomaly detection adds complexity without clear ROI | Low | Keep it optional; use a simple z-score threshold as fallback; scikit-learn is lightweight |
| Scope creep: too many new technologies | High | Stick to the planned phases. Terraform is scoped to a single AWS provider with minimal modules; no multi-cloud or advanced networking.

---

## 9. Immediate Next Step

**Phase 1, Task 1.1:** Instrument FastAPI with Prometheus histograms and counters.

Awaiting your mark to proceed.
