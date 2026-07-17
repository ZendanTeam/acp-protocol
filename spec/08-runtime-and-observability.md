# ACP Runtime & Observability Specification
**Document Number:** RFC-ACP-008  
**Version:** 1.0.0  

---

## 1. Universal Execution Runtime Architecture

The **ACP Runtime** provides a uniform execution abstraction layer that allows identical agent logic and workflow DAGs to run seamlessly across highly diverse physical and virtual compute environments—from cloud Kubernetes clusters down to constrained edge micro-controllers and web browsers.

```
+---------------------------------------------------------------------------------------------------+
|                                        ACP UNIVERSAL RUNTIME                                      |
|                                                                                                   |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|  |  DOCKER & K8S      |  |     SERVERLESS     |  |     BARE METAL     |  |    EDGE & IOT       |  |
|  |  (OCI Pods, Helm)  |  |  (Lambda, Workers) |  |  (Linux cgroups v2)|  |  (Wasm / Micro-ROS) |  |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|            ^                       ^                       ^                        ^             |
|            |                       |                       |                        |             |
|            +-----------------------+-----------+-----------+------------------------+             |
|                                                |                                                  |
|                                                v                                                  |
|                      +---------------------------------------------------+                        |
|                      |             MOBILE, DESKTOP & BROWSER             |                        |
|                      |      (iOS/Android Swift/Kotlin, Electron, Wasm)   |                        |
|                      +---------------------------------------------------+                        |
+---------------------------------------------------------------------------------------------------+
```

### 1.1 Runtime Target Specifications
- **Docker & Kubernetes (`K8s`):** The primary enterprise runtime. Each agent executes as an isolated OCI container within a Kubernetes Pod. The ACP Host runs as a Kubernetes DaemonSet, auto-scaling agent replicas using Horizontal Pod Autoscalers (`HPA`) driven by real-time broker queue depths and CPU/VRAM metrics.
- **Serverless (`Lambda` / `Cloudflare Workers`):** For event-driven or bursty agent workloads, the ACP Runtime compiles agent handlers to WebAssembly (`Wasm`) or lightweight Python binaries (`<15ms` cold start), invoking them stateless upon ingress frame arrival.
- **Bare Metal:** High-performance local execution on physical GPU servers. The Host leverages Linux **cgroups v2** and **network namespaces** to enforce resource budgets directly without container virtualization overhead.
- **Edge Devices & IoT (`Raspberry Pi` / `Micro-controllers`):** The ACP Runtime operates in **Lite Mode**, utilizing Wasm (`WASI-micro`) or native C/Rust binaries over low-overhead UDP/BLE transports to execute real-time robot and sensor loops.
- **Mobile (`iOS` / `Android`) & Desktop (`macOS` / `Windows` / `Linux`):** Native SDK bindings allow background agent services to run locally on consumer devices, coordinating via local Unix domain sockets or loopback WebSockets while respecting OS battery and background execution policies.
- **Browser (`WebAssembly` / `Web Workers`):** The entire ACP client and agent runtime compiles to Wasm, running securely inside Web Workers (`sandbox="allow-scripts"`). Communication occurs via `WebSockets` to cloud gateways or `WebRTC/DataChannels` for direct P2P browser-to-browser agent collaboration.

---

## 2. Enterprise Observability & OpenTelemetry Suite

To debug, trace, and monitor distributed workflows spanning thousands of independent agents across multiple clouds, ACP requires full observability at every layer. ACP natively embeds **OpenTelemetry (`OTel`) W3C specifications** directly into the protocol wire envelope.

```
+---------------------------------------------------------------------------------------------------+
|                                 ACP OBSERVABILITY DATA PIPELINE                                   |
|                                                                                                   |
|  [ ACP Agent / Host / Gateway / Router / Broker / Memory Service ]                                |
|        |                                                                                          |
|        +---> Traces (W3C TraceContext traceparent header: 00-4bf92f35...-01)                      |
|        +---> Metrics (Prometheus / OTel Metric Data Model)                                        |
|        +---> Logs (Structured JSON Log Records with Cryptographic Hashes)                         |
|        +---> Profiling (Continuous CPU / VRAM / Memory Allocation Profiles)                       |
|        |                                                                                          |
|        v                                                                                          |
|  +---------------------------------------------------------------------------------------------+  |
|  |                       ACP TELEMETRY COLLECTOR (OTel Collector Daemon)                       |  |
|  +---------------------------------------------------------------------------------------------+  |
|        |                         |                         |                         |            |
|        v                         v                         v                         v            |
|  +-----------+             +-----------+             +-----------+             +-----------+  |
|  |  JAEGER   |             |PROMETHEUS |             | ELASTIC / |             |  GRAFANA  |  |
|  | (Traces)  |             | (Metrics) |             | LOKI (Logs|             | DASHBOARD |  |
|  +-----------+             +-----------+             +-----------+             +-----------+  |
+---------------------------------------------------------------------------------------------------+
```

### 2.1 Distributed Tracing (`W3C Trace Context`)
Every ACP frame envelope includes `routing.trace_parent` matching the W3C Trace Context standard:
```
trace_parent: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
              ver - trace_id (16 bytes hex)         - parent_id (8 bytes) - flags (01=recorded)
```
Whenever an agent emits a child request, delegates a workflow task, or writes to memory, it inherits `trace_id`, generates a new `parent_id` span, and transmits the context. Tracing dashboards (`Jaeger` / `Zipkin`) reconstruct exact end-to-end multi-agent execution graphs across every network hop and component.

### 2.2 Standardized Prometheus Metrics
All ACP components automatically expose a `/metrics` endpoint formatted to Prometheus / OTel metrics standards:
- **`acp_frames_total{frame_type, status, sender_did}`:** Counter tracking total frames sent/received.
- **`acp_frame_duration_seconds{action, target_type}`:** Histogram measuring end-to-end processing latency.
- **`acp_workflow_dag_duration_seconds{workflow_id, status}`:** Histogram measuring DAG completion time.
- **`acp_memory_query_latency_ms{memory_tier, operation}`:** Histogram tracking distributed memory SLAs.
- **`acp_broker_queue_depth{topic}`:** Gauge indicating pending messages in event topics.
- **`acp_agent_cost_credits_total{did, skill_id}`:** Counter tracking real-time economic consumption.

### 2.3 Continuous Profiling & Health Checks
- **Continuous Profiling (`py-spy` / `pprof` / `ebpf`):** ACP Hosts continuously sample CPU stack traces, VRAM allocations, and memory leaks of running agent processes, exporting low-overhead profiles to central dashboards (`Pyroscope`).
- **Liveness & Readiness Probes (`/healthz` and `/readyz`):** 
  - `Liveness Probe`: Returns `200 OK` if the Host/Gateway process is running and responsive.
  - `Readiness Probe`: Returns `200 OK` only after the agent has loaded required models into memory, synced current vector index replicas, and established quorum with the ACP Registry.

### 2.4 Live Monitoring Dashboard & Circuit Breakers
The **ACP Live Monitoring Dashboard** aggregates telemetry streams to provide operational visibility and automated fault mitigation:
- **Real-Time Topology Visualization:** Interactive force-directed mesh graph showing live data flows between agents, routers, and databases.
- **Automated Circuit Breaker State Machine:**
  - `CLOSED (Normal):` Requests flow freely.
  - `OPEN (Tripped):` If an agent's failure rate exceeds `15%` within `60 seconds` or P99 latency spikes above `10,000ms`, the Gateway trips the circuit breaker (`CircuitBreakerState: OPEN`). Incoming requests are rejected instantly with `503 Service Unavailable - Circuit Breaker Tripped` or rerouted to a backup fallback agent.
  - `HALF-OPEN (Recovery):` After a `30-second` cooldown, the Gateway allows `5%` of traffic through to test recovery before restoring full `CLOSED` status.
