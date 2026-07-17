# ACP Components & Roles Deep-Dive Specification
**Document Number:** RFC-ACP-002  
**Version:** 1.0.0  

---

## 1. Complete Architectural Component Topology

The ACP specification defines fifteen distinct, highly cohesive, and loosely coupled components. Each component can be deployed as an independent cloud microservice, co-located inside a single monolithic host process for edge devices, or scaled out across Kubernetes clusters.

```
+-------------------------------------------------------------------------------------------------------------+
|                                              ACP CLOUD / EDGE                                               |
|                                                                                                             |
|  +--------------------+    +--------------------+    +--------------------+    +-------------------------+  |
|  | ACP IDENTITY PROV. |    |    ACP REGISTRY    |    |   ACP DISCOVERY    |    |     ACP MARKETPLACE     |  |
|  | (DIDs, JWT, Caps)  |    | (Manifest Store)   |    | (Gossip/mDNS/Query)|    | (Skills, Templates, WFs)|  |
|  +--------------------+    +--------------------+    +--------------------+    +-------------------------+  |
|            ^                         ^                         ^                            ^               |
|            |                         |                         |                            |               |
|  +-------------------------------------------------------------------------------------------------------+  |
|  |                                          ACP GATEWAY (Inbound/Outbound Edge Security, TLS Term, RBAC) |  |
|  +-------------------------------------------------------------------------------------------------------+  |
|            ^                                                                                ^               |
|            v                                                                                v               |
|  +-------------------------------------------------------------------------------------------------------+  |
|  |                                          ACP ROUTER (Mesh Routing Table, Skill Routing, Multicast)    |  |
|  +-------------------------------------------------------------------------------------------------------+  |
|            ^                         ^                         ^                            ^               |
|            v                         v                         v                            v               |
|  +-------------------+     +-------------------+     +--------------------+       +----------------------+  |
|  |     ACP HOST 1    |     |     ACP HOST 2    |     |    ACP SCHEDULER   |       |      ACP BROKER      |  |
|  | +---------------+ |     | +---------------+ |     | (DAG Execution,    |       | (Event Bus, Pub/Sub, |  |
|  | |  ACP Runtime  | |     | |  ACP Runtime  | |     |  Parallel Workers, |       |  Topic Streams,      |  |
|  | | +-----------+ | |     | | +-----------+ | |     |  Retry, Rollback)  |       |  DLQ, Checkpoints)   |  |
|  | | | ACP Agent | | |     | | | ACP Agent | | |     +--------------------+       +----------------------+  |
|  | | +-----------+ | |     | | +-----------+ | |               ^                              ^               |
|  | +---------------+ |     | +---------------+ |               |                              |               |
|  +-------------------+     +-------------------+               +---------------+--------------+               |
|            ^                         ^                                         |                              |
|            +-------------------------+-----------------------------------------+                              |
|                                      |                                                                        |
|                                      v                                                                        |
|  +-------------------------------------------------------------------------------------------------------+  |
|  | ACP MEMORY SERVICE (Short-Term LRU, Long-Term KV, Vector Cosine Sim, Knowledge Graph, Snapshots, Sync)|  |
|  +-------------------------------------------------------------------------------------------------------+  |
|                                      ^                                                                        |
|                                      | Observability Streams (OTel Traces, Metrics, Logs)                     |
|                                      v                                                                        |
|  +-------------------------------------------------------------------------------------------------------+  |
|  | ACP OBSERVABILITY SUITE: [ ACP Monitoring ] <---> [ ACP Logging ] <---> [ ACP Telemetry (OTel Collector)]|  |
|  +-------------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------------+
```

---

## 2. Component Specifications

### 2.1 ACP Host
- **Role & Responsibilities:** The physical or virtual daemon process that supervises one or more ACP Runtimes. The Host provides system-level resource isolation (CPU, memory, disk limits), manages OS-level network sockets, handles process lifecycle (spawn, heartbeat check, graceful shutdown), and enforces global security sandboxing rules (e.g., cgroups, seccomp filters).
- **Technical Specifications:**
  - Exposes an admin control plane endpoint (`/acp/v1/host/status`) secured via mutual TLS (`mTLS`).
  - Periodically reports hardware health metrics (CPU utilization, available VRAM, memory pressure) to the ACP Discovery service to enable load-aware task scheduling.
  - Automatically restarts crashed Agent Runtimes using exponential backoff (`max_retries=5`).

### 2.2 ACP Agent
- **Role & Responsibilities:** The autonomous domain entity possessing a unique Decentralized Identifier (`did:acp:...`), a defined capability manifest (`agent-manifest.schema.json`), and an underlying intelligence model (e.g., LLM, vision model, or deterministic state machine).
- **Technical Specifications:**
  - Operates statelessly with respect to long-term data; all state mutations are persisted to the ACP Memory Service using partition keys derived from the session ID.
  - Emits health heartbeats (`frame_type: HEARTBEAT`) every 10 seconds.
  - Strictly validates inbound Capability Tokens before executing any action.

### 2.3 ACP Gateway
- **Role & Responsibilities:** The ingress/egress perimeter defense proxy for an ACP Cluster or organization.
- **Technical Specifications:**
  - Terminates external transport protocols (HTTPS, TLS, WebSocket, QUIC) and translates them into internal high-performance framing (`gRPC`/`HTTP2` with binary payload wrapping).
  - Enforces authentication (`auth_token` verification against the IdP JWKS endpoint), rate limiting (token bucket: e.g., 10,000 frames/sec per tenant DID), and cryptographic replay prevention (checking `message_id` + `nonce` against an eviction cache).
  - Performs schema validation (`envelope.schema.json`) on ingress frames, immediately dropping malformed messages before they reach internal brokers.

### 2.4 ACP Router
- **Role & Responsibilities:** The distributed routing plane responsible for finding the optimal target endpoint for any message.
- **Technical Specifications:**
  - Maintains a dynamic routing table updated via gossip protocols or registry subscriptions.
  - Supports **Direct DID Routing** (`receiver.target_id = "did:acp:finance-agent-1"`).
  - Supports **Skill-Based Dynamic Routing** (`receiver.routing_query = {"required_skills": ["sql_optimization"], "max_latency_ms": 200}`). The router evaluates candidate agents in real-time and forwards the frame to the agent offering the lowest cost or lowest latency SLA.
  - Enforces `hop_count <= max_hops` (default 16) and appends its node ID to `routing.router_path` to prevent infinite routing loops.

### 2.5 ACP Registry
- **Role & Responsibilities:** The authoritative, highly available catalog of verified Agent Manifests (`agent-manifest.schema.json`).
- **Technical Specifications:**
  - Backed by an ACID-compliant consensus datastore (e.g., etcd, Raft cluster, or PostgreSQL with read replicas).
  - Stores agent public keys (`pubkey_base64`), skill schemas, and security profiles.
  - Emits `REGISTRY_UPDATED` events on the ACP Broker whenever an agent registers, updates its manifest, or is deregistered due to missed heartbeats.

### 2.6 ACP Discovery
- **Role & Responsibilities:** The real-time discovery engine enabling agents to locate nearby peers, available compute clusters, vector stores, and specialized capabilities.
- **Technical Specifications:**
  - Implements a hybrid discovery protocol:
    - **Local Network:** Multicast DNS (`mDNS` / DNS-SD on UDP port 5353) for edge/local discovery (`_acp._tcp.local.`).
    - **Cloud/Mesh:** Epidemic Gossip protocol (`SWIM` / `Serf`) for cluster-level topology dissemination.
    - **Global/Query:** REST/gRPC queries against the ACP Registry (`/acp/v1/discovery/query`).

### 2.7 ACP Memory Service
- **Role & Responsibilities:** The unified distributed memory plane for all agents across the mesh.
- **Technical Specifications:**
  - Partitions memory into six distinct tiers: **Short-Term (LRU cache)**, **Long-Term (Key-Value store)**, **Shared (Pub/Sub synchronized state)**, **Vector (Cosine/L2 embedding index)**, **Knowledge Graph (Resource Description Framework / Labeled Property Graph triples)**, and **Encrypted (AES-256-GCM enclave storage)**.
  - Supports multi-master replication with Conflict-Free Replicated Data Types (`CRDTs` / LWW-Element-Set) or Raft consensus depending on consistency tier.
  - Automatic Time-To-Live (`TTL`) expiration and point-in-time state snapshots (`CREATE_SNAPSHOT` / `RESTORE_SNAPSHOT`).

### 2.8 ACP Scheduler
- **Role & Responsibilities:** The distributed workflow and task execution engine.
- **Technical Specifications:**
  - Evaluates Directed Acyclic Graphs (`workflow-dag.schema.json`), calculating topological ordering and dependency satisfaction.
  - Dispatches independent nodes in parallel (`execution_type: PARALLEL_JOIN`).
  - Manages automatic task retries (`exponential backoff`), voting consensus gates (`VOTING_GATE`), and compensating rollback workflows (`rollback_action`) upon node failures.

### 2.9 ACP Broker
- **Role & Responsibilities:** The high-throughput asynchronous event bus (`Kafka` / `NATS JetStream` / `RabbitMQ` compatible architectural abstraction).
- **Technical Specifications:**
  - Manages persistent publish/subscribe topics (e.g., `acp.events.workflow.status`, `acp.streams.audio.chunk`).
  - Provides at-least-once or exactly-once delivery semantics via explicit consumer acknowledgments (`ACK` / `NACK`).
  - Automatically routes undeliverable or repeatedly failed frames to a Dead Letter Queue (`DLQ`) topic after 5 failed delivery attempts.

### 2.10 ACP Identity Provider (IdP)
- **Role & Responsibilities:** The root of trust for all cryptographic identities, authentication tokens, and authorization claims.
- **Technical Specifications:**
  - Implements OpenID Connect (`OIDC`) and OAuth2 specifications tailored for autonomous agent workloads (Client Credentials Grant & Token Exchange `RFC 8693`).
  - Mints and verifies Decentralized Identifiers (`DID` W3C specification `did:acp:...`) and signed zero-trust **Capability Tokens** (`capability-token.schema.json`).
  - Manages cryptographic keys, rotating public key JSON Web Key Sets (`JWKS`) every 24 hours while maintaining 7-day backward verification compatibility.

### 2.11 ACP Marketplace
- **Role & Responsibilities:** The decentralized or federated repository for sharing, monetizing, and installing agent skills, workflows, and templates.
- **Technical Specifications:**
  - Stores cryptographically signed packages (tarballs/OCI artifacts containing JSON schemas, prompt templates, and Wasm/Python plugin binaries).
  - Verifies publisher cryptographic signatures and runs automated sandboxed vulnerability scanning on all uploaded plugins before publishing to the catalog.

### 2.12 ACP Runtime
- **Role & Responsibilities:** The execution environment isolating and running the actual agent application logic.
- **Technical Specifications:**
  - Pluggable runtime backends:
    - **Container/Docker/K8s:** Standard OCI container execution with strict CPU/memory limits and read-only root filesystems.
    - **Serverless/Micro-VM:** AWS Lambda, Cloudflare Workers, or Firecracker micro-VMs with `<10ms` cold starts.
    - **Wasm:** WebAssembly System Interface (`WASI`) sandbox for ultra-secure, deterministic edge and browser execution.
  - Intercepts all outgoing network requests made by the agent and redirects them through the local ACP Gateway to enforce authorization and audit logging.

### 2.13 ACP Monitoring
- **Role & Responsibilities:** Real-time health checking, anomaly detection, and live system status tracking.
- **Technical Specifications:**
  - Continually polls or receives heartbeats from all active Hosts, Routers, Gateways, and Agents.
  - Calculates rolling SLA metrics (P50, P95, P99 frame latencies, error percentages, broker queue depths).
  - Triggers automated circuit breakers (`CircuitBreakerState: OPEN`) when an agent's error rate exceeds 15% over a 60-second window, preventing cascading failures.

### 2.14 ACP Logging
- **Role & Responsibilities:** Secure, tamper-evident audit logging for compliance, forensic analysis, and debugging.
- **Technical Specifications:**
  - Ingests structured JSON logs from every component (`syslog` / `stdout` / OTel Log Data Model).
  - Every log record includes `message_id`, `correlation_id`, `sender.agent_id`, `timestamp_ns`, and cryptographic proof.
  - Logs are appended to an immutable, write-once-read-many (`WORM`) storage sink with SHA-256 hash chaining to ensure tamper detection.

### 2.15 ACP Telemetry
- **Role & Responsibilities:** OpenTelemetry (`OTel`) collector and metrics aggregator.
- **Technical Specifications:**
  - Collects distributed traces using the W3C Trace Context standard (`traceparent` header propagation: `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`).
  - Exports Prometheus-compatible metrics (`acp_frames_total`, `acp_frame_duration_seconds`, `acp_memory_query_latency_ms`, `acp_workflow_dag_duration_seconds`).
  - Seamlessly integrates with Grafana, Jaeger, Zipkin, and Datadog.
