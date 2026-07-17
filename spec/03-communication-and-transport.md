# ACP Communication, Networking & Streaming Specification
**Document Number:** RFC-ACP-003  
**Version:** 1.0.0  

---

## 1. Agent Communication Patterns & Semantics

ACP establishes precise wire-level semantics and capability claims for nine fundamental communication vectors:

### 1.1 Agent -> Agent
- **Semantic:** Peer-to-peer or routed autonomous collaboration, negotiation, or task delegation.
- **Wire Pattern:** Bi-directional asynchronous streaming (`STREAM_CHUNK`) or request-response (`REQUEST` / `RESPONSE`).
- **Security Claim Required:** `CapabilityToken` containing target agent DID (`did:acp:target`) and action (`EXECUTE`, `DELEGATE`, or `NEGOTIATE`).

### 1.2 Agent -> Human
- **Semantic:** Human-in-the-loop (`HITL`) approval gates, clarification queries, or interactive notifications.
- **Wire Pattern:** `REQUEST` sent to a human inbox/UI topic, followed by an asynchronous `RESPONSE` containing the human's decision (`APPROVE` / `REJECT` / `MODIFY`).
- **Timeout Behavior:** If human response is not received within `timeout_ms` (e.g., 24 hours), the frame triggers the workflow's configured escalation or rollback policy.

### 1.3 Agent -> Tool
- **Semantic:** Invoking atomic stateless or stateful execution capabilities (e.g., code interpreter, web search, calculator).
- **Wire Pattern:** Synchronous `REQUEST` / `RESPONSE` or streaming token output (`STREAM_CHUNK`).
- **Sandboxing Guarantee:** Tools execute inside isolated subprocesses or WebAssembly containers (`WASI`) with strictly bounded memory and zero unauthorized host filesystem access.

### 1.4 Agent -> Database
- **Semantic:** Querying or mutating relational, NoSQL, or vector databases.
- **Wire Pattern:** `REQUEST` with SQL/Cypher/JSON query payload, returning structured row sets (`RESPONSE`) or streaming cursors (`STREAM_CHUNK`).
- **Security & RBAC:** Database drivers integrated with ACP Gateways intercept queries, verifying that the agent's Capability Token authorizes access to the requested table/schema namespace (`abac_claims.allowed_tables`).

### 1.5 Agent -> API
- **Semantic:** Calling third-party HTTP/REST/GraphQL or SOAP web endpoints.
- **Wire Pattern:** The agent sends an `API_INVOCATION` request frame to the ACP Gateway; the Gateway injects required secrets from the Secrets Vault (`secrets://api-keys/stripe_key`) and proxies the request via HTTPS, returning the exact response to the agent.

### 1.6 Agent -> Browser
- **Semantic:** Remote browser automation (Playwright/Puppeteer/Selenium style headless or headed DOM interaction, screenshotting, scraping, and clicking).
- **Wire Pattern:** Bi-directional `STREAM_CHUNK` framing transporting DOM events, accessibility trees, base64/JPEG screenshots, and user simulation commands (`CLICK`, `TYPE`, `NAVIGATE`).

### 1.7 Agent -> Robot
- **Semantic:** Cyber-physical systems control (`ROS2` / `Micro-ROS` bridge for drones, robotic arms, autonomous vehicles).
- **Wire Pattern:** Real-time UDP or QUIC low-latency streaming frames (`content_type: application/octet-stream`) transporting velocity/position setpoints (`Twist` messages) and sensor telemetry (LiDAR, camera frames, IMU).
- **SLA Enforcement:** Frames carry strict `ttl_ms: 50` (50 milliseconds). Expired control frames are dropped immediately to prevent stale velocity commands from causing physical hazards.

### 1.8 Agent -> Cluster
- **Semantic:** Submitting bulk batch processing jobs or MapReduce-style parallel worker invocations across an ACP compute cluster.
- **Wire Pattern:** `TASK_DELEGATION` frame addressed to `receiver.target_type = "CLUSTER"`, containing `input_data` array and worker scaling parameters (`min_replicas: 10, max_replicas: 100`).

### 1.9 Agent -> Cloud
- **Semantic:** Provisioning or resizing cloud infrastructure (storage buckets, compute instances, serverless endpoints) or triggering cloud provider services.
- **Wire Pattern:** `REQUEST` payload directed to cloud provider control planes (`aws://ec2/launch`, `gcp://storage/bucket/create`) authenticated via OIDC federation (`AWS IAM Role Web Identity`).

---

## 2. Networking & Transport Layer Specifications

ACP decouples protocol framing (`envelope.schema.json`) from the physical transport. Every ACP Host and Gateway must support multiple transport bindings, negotiating the optimal transport at runtime during initial peer handshake:

```
+---------------------------------------------------------------------------------------------------+
|                                      ACP APPLICATION LAYER                                        |
|                          (Envelope Schema, Signatures, Capability Tokens)                         |
+---------------------------------------------------------------------------------------------------+
|                                    ACP TRANSPORT ADAPTER LAYER                                    |
+---------------+---------------+---------------+---------------+---------------+---------------+---+
|   HTTP/1.1    |    HTTP/2     |    HTTP/3     |     QUIC      |     gRPC      |   WebSocket   | ...
| (POST /json)  | (Multiplexed) |  (UDP/QUIC)   | (Low Latency) |  (Protobuf)   |  (Realtime)   |
+---------------+---------------+---------------+---------------+---------------+---------------+---+
|  Unix Socket  |   TCP Stream  |  UDP Datagram |   Bluetooth   |     mDNS      |   P2P Mesh    |
|  (IPC Local)  |  (Direct Net) | (Realtime/SLA)| (Edge/Mobile) |  (Local Net)  | (Gossip/LibP2P)|
+---------------+---------------+---------------+---------------+---------------+---------------+---+
```

### 2.1 Transport Bindings & Characteristics
- **HTTP/1.1 & HTTP/2:** Standard REST-like binding (`POST /acp/v1/frame`). HTTP/2 leverages stream multiplexing to send concurrent requests and streaming chunks over a single TCP connection.
- **HTTP/3 & QUIC:** Preferred cloud transport. Runs over UDP, eliminating TCP head-of-line blocking and enabling `0-RTT` connection resumption during agent mobility across edge networks.
- **gRPC:** Preferred internal microservice transport. Envelopes and payloads are serialized using high-performance Protocol Buffers (`acp.wire.Envelope`) over HTTP/2 with bi-directional streaming support.
- **WebSocket:** Preferred browser and desktop UI transport (`wss://host/acp/ws`). Envelopes are transmitted as text JSON frames or binary frames.
- **Unix Domain Socket (`AF_UNIX`):** Preferred local inter-process communication (`IPC`) transport when Host, Router, and Agent run on the same physical/virtual machine (`/var/run/acp/acp.sock`), achieving `<0.1ms` latency and `>10 GB/s` throughput.
- **TCP Stream:** Raw socket connection with length-prefixed binary frame headers (`4-byte big-endian frame length` followed by UTF-8 envelope JSON or Wasm binary).
- **UDP Datagram:** High-speed, loss-tolerant transport (`max payload 1400 bytes` to fit within standard Ethernet MTU without fragmentation) used for high-frequency robot telemetry and streaming audio/video frames.
- **Bluetooth Low Energy (BLE):** Edge/IoT transport (`GATT server` exposing ACP Write and Notify characteristics) for disconnected local mesh environments.
- **Local Network Discovery (mDNS/DNS-SD):** Agents announce existence on UDP port `5353` under service name `_acp._tcp.local.`, containing TXT records with `did`, `version`, and `supported_transports`.
- **P2P & Mesh Networking (`libp2p` / Gossip):** Decentralized peer-to-peer overlay network enabling agents to route frames across NATs and firewalls via DHT (Distributed Hash Table) node lookups, STUN/TURN traversal, and multi-hop relay.

---

## 3. Native Multi-Modal Streaming Architecture

In modern autonomous workflows, waiting for an agent or tool to generate its complete output before sending a response introduces unacceptable latency. ACP is **Streaming-First by design**:

### 3.1 Stream Lifecycle & Framing
A stream session consists of three phases:
1. **Initiation (`REQUEST` with `stream_requested: true`):** Sender asks receiver to begin streaming.
2. **Chunk Transmission (`STREAM_CHUNK`):** Receiver emits sequential frames containing `sequence_number` (0, 1, 2...), `stream_id` (matching `correlation_id`), `content_type`, and `data`.
3. **Termination (`STREAM_END` or `ERROR`):** Receiver emits a final frame with `is_final: true` containing aggregate telemetry (`total_tokens_emitted`, `duration_ms`).

### 3.2 Supported Multi-Modal Content Types
- `text/plain` & `application/json`: Real-time text generation chunks or progressive structured JSON construction.
- `application/acp-tokens`: Sub-word or token-level LLM streaming with token logprobs and attention metadata.
- `audio/wav` & `audio/opus`: Low-latency 16 kHz or 48 kHz PCM audio streams for real-time voice conversations (`SLA latency < 150ms`).
- `video/h264`: Raw or containerized video frame bursts for vision inspection and robot navigation.
- `application/acp-event`: Real-time domain events emitted during long-running background tasks (e.g., `git_clone_progress: 45%`, `docker_build_layer: 3/8`).
- `application/octet-stream`: High-speed binary transfers for model weights, vector index embeddings, or file uploads.

### 3.3 Backpressure Control
To prevent fast producers (e.g., GPU cluster streaming tokens) from overwhelming slow consumers (e.g., mobile edge agent over cellular network), ACP streams implement **Credit-Based Flow Control**:
- The consumer sends a `FLOW_CONTROL` control frame indicating `credits_granted: N` (number of chunks it is willing to buffer).
- The producer decrements its credit counter for each transmitted `STREAM_CHUNK`. When `credits == 0`, the producer pauses transmission until the consumer emits another `FLOW_CONTROL` frame replenishing credits.
