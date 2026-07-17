# ACP (Agent Collaboration Protocol) Architecture & Vision Specification
**Document Number:** RFC-ACP-001  
**Version:** 1.0.0  
**Status:** Standards Track / Open Specification  
**Date:** 2026-07-17  

---

## 1. Executive Summary & Vision

The **Agent Collaboration Protocol (ACP)** is a brand-new, open, language-agnostic, and transport-agnostic standard designed from the ground up to serve as the distributed operating protocol and runtime fabric for autonomous AI agents. 

While existing protocols focus heavily on single-node or client-server interactions, ACP is engineered to enable thousands of autonomous, heterogeneous agents to securely discover each other, negotiate terms, delegate tasks, execute complex Directed Acyclic Graph (DAG) workflows, share distributed memory, and synchronize state across machines, clouds, edge clusters, and enterprise boundaries without central bottlenecks.

### 1.1 The Analogy: What is ACP?
Think of ACP as:
- **Kubernetes for AI Agents:** Providing orchestration, lifecycle management, sandboxed execution, auto-scaling, fault tolerance, and self-healing topologies for autonomous worker agents.
- **HTTP + gRPC + OAuth + Event Bus for Autonomous AI:** Combining unified wire framing, asynchronous streaming, zero-trust cryptographic capability authorization, and publish/subscribe messaging into a single coherent protocol suite.
- **A Distributed Runtime Rather Than Only a Tool-Calling Protocol:** Providing the underlying infrastructure for memory replication, decentralized peer-to-peer discovery, economic negotiation, multi-agent voting gates, and cryptographic auditability.

---

## 2. Why Not MCP? Solving Problems Outside MCP's Scope

The **Model Context Protocol (MCP)** has emerged as an effective mechanism for connecting a single AI client application (such as an IDE or chat frontend) to local or remote servers providing context, prompts, and atomic tool calls. However, MCP intentionally restricts its scope to client-to-server (`1:1`) request-response patterns over local stdio or SSE/HTTP.

ACP does not duplicate or compete with MCP for local prompt context attachment. Instead, ACP solves foundational distributed systems challenges that arise when **multiple autonomous agents** must collaborate across compute networks:

| Architectural Dimension | Model Context Protocol (MCP) | Agent Collaboration Protocol (ACP) | Technical Reasoning for ACP Design |
| :--- | :--- | :--- | :--- |
| **Topological Model** | Client-Server (`1:1` or `1:N` star topology where client is single point of control) | Distributed Peer-to-Peer, Mesh, and Hierarchical Clusters (`N:M`) | Agents in a mesh must initiate communication independently without relying on a monolithic central orchestrator that would become a performance bottleneck and single point of failure. |
| **Primary Interaction Pattern** | Synchronous Request-Response (Tool calling & Resource fetching) | Asynchronous Event-Driven, Streaming-First, Negotiated Workflows, Multi-Agent Voting | Complex multi-step agent workflows require long-running, non-blocking asynchronous execution where tasks take minutes or hours and require dynamic status streams. |
| **Identity & Security** | Basic OAuth / API keys or implicit trust via local `stdio` processes | **Zero-Trust Architecture:** DIDs (`did:acp:...`), Ed25519/ECDSA frame signing, Capability Tokens, mTLS, and RBAC/ABAC | In multi-tenant cloud and federation environments, no node can be implicitly trusted. Every message must be cryptographically signed, verifiable, and strictly scoped via capability tokens. |
| **Orchestration & Workflows** | None (Left entirely to the client application LLM loop) | **Native Distributed Workflow Engine:** Task delegation, DAG execution, voting consensus gates, automatic retries, checkpoints, and rollback actions | Delegating multi-step workflows requires protocol-level semantics for execution guarantees, error propagation, compensating transactions (rollbacks), and voting consensus. |
| **Memory Architecture** | Resource queries (`resources/read`) without shared state synchronization | **Multi-Tier Distributed Memory:** Short-Term LRU, Long-Term KV, Vector Cosine Similarity, Knowledge Graph, with replication, synchronization, and snapshots | Agents collaborating on long-running tasks need unified, synchronized access to shared semantic memory, vector embeddings, and entity relationships across distributed nodes. |
| **Discovery & Negotiation** | Static list of tools via `tools/list` at initialization | **Dynamic Gossip, mDNS, and Registry Discovery:** Querying by skill capabilities, compute requirements, SLA metrics, and real-time economic negotiation | In a dynamic agent cloud, agents enter and leave the network continuously. Agents must discover optimal peers dynamically based on real-time cost, latency SLAs, and skill compatibility. |
| **Network Transports** | `stdio` and HTTP/SSE | **Transport-Agnostic Wire Framing:** HTTP/1.1/2/3, QUIC, gRPC, WebSockets, Unix Sockets, TCP/UDP, P2P Mesh | Different execution targets (cloud clusters vs. edge IoT devices vs. browser workers) require varied network protocols; ACP abstracts the transport via a universal wire frame. |

---

## 3. Core Principles

ACP adheres to twelve uncompromising core engineering principles:

1. **Open Standard:** Free, unencumbered, governed by open RFCs, JSON Schemas (`draft-2020-12`), and public wire specifications suitable for cross-vendor enterprise adoption.
2. **Language Agnostic:** Formalized via exact wire structures and JSON/Protobuf schemas allowing idiomatic SDKs across Go, Rust, C#, Java, Kotlin, Swift, Python, JS/TS, PHP, Ruby, Lua, C, and C++.
3. **Transport Agnostic:** The Universal ACP Frame Envelope operates identically whether transmitted over HTTP/2 POST, a QUIC stream, gRPC bi-directional stream, WebSocket connection, or Unix domain socket.
4. **Cloud Native:** Designed to run seamlessly in Docker containers, Kubernetes Pods, AWS/GCP/Azure serverless functions, edge micro-VMs (Firecracker), and WebAssembly (Wasm) runtimes.
5. **Event Driven:** Every component communicates via immutable event streams and asynchronous message passing rather than blocking RPCs, maximizing throughput and resilience.
6. **Distributed:** Stateless horizontal scaling at the Host, Router, and Memory tiers ensures zero single-point-of-failure (`SPOF`) topologies.
7. **Secure by Default:** Cryptographic signing of every frame (`Ed25519` / `ECDSA`), mandatory TLS 1.3 or QUIC encryption (`mTLS`), and strict validation of zero-trust Capability Tokens.
8. **Zero Trust:** Every agent, host, and human client must prove identity (`did:acp:...`) and permissions (`RBAC`/`ABAC`) for every single frame and operation.
9. **Backward Extensible:** Strict semantic versioning (`acp_version`), feature negotiation headers, and permissive JSON schema payload handling ensure new capabilities do not break existing deployments.
10. **Versioned:** Protocol envelopes, agent manifests, skills, and workflow DAGs carry explicit semantic versions (`vMajor.Minor.Patch`).
11. **Streaming First:** Native support for chunked multi-modal streaming (text tokens, PCM/WAV audio chunks, H.264 video frames, and structured binary arrays) with backpressure control.
12. **Async First:** Long-running operations immediately return a `correlation_id` and deliver progress updates via asynchronous event callbacks or streams rather than holding HTTP/RPC threads open.

---

## 4. High-Level Architectural Topology

```
+---------------------------------------------------------------------------------------------------+
|                                      ACP DISTRIBUTED MESH                                         |
|                                                                                                   |
|  +------------------------+      mTLS / QUIC / gRPC      +------------------------+             |
|  |       ACP HOST A       | <--------------------------> |       ACP HOST B       |             |
|  |  +------------------+  |                              |  +------------------+  |             |
|  |  |    ACP Router    |  |       Gossip Discovery       |  |    ACP Router    |  |             |
|  |  +------------------+  | <--------------------------> |  +------------------+  |             |
|  |  |    ACP Gateway   |  |                              |  |    ACP Gateway   |  |             |
|  |  +------------------+  |                              |  +------------------+  |             |
|  |  |  Agent Runtime   |  |      Event Bus / Broker      |  |  Agent Runtime   |  |             |
|  |  | +--------------+ |  | <--------------------------> |  | +--------------+ |  |             |
|  |  | | Agent Alpha  | |  |                              |  | | Agent Beta   | |  |             |
|  |  | +--------------+ |  |                              |  | +--------------+ |  |             |
|  |  +------------------+  |                              |  +------------------+  |             |
|  +------------------------+                              +------------------------+             |
|              ^                                                       ^                            |
|              | Capability Checks & Audit                             | Distributed Memory Sync    |
|              v                                                       v                            |
|  +------------------------+                              +------------------------+             |
|  |  ACP IDENTITY PROVIDER |                              |   ACP MEMORY SERVICE   |             |
|  |  (DID, JWT, CapToken)  |                              | (Vector, KG, Short/Long|             |
|  +------------------------+                              +------------------------+             |
+---------------------------------------------------------------------------------------------------+
```

---

## 5. Universal Wire Frame Envelope

All communication in ACP—regardless of underlying transport—is encapsulated within the **Universal ACP Frame Envelope**. This ensures intermediate routers, logging monitors, security gateways, and brokers can inspect headers, verify cryptographic signatures, and enforce rate limits without deserializing or violating end-to-end encrypted payloads.

### 5.1 Envelope Structure (`envelope.schema.json`)
Every ACP message must conform to the following top-level fields:
- `acp_version`: The semantic specification version (`1.0.0`).
- `message_id`: A globally unique KSUID or UUIDv4 identifying the frame.
- `correlation_id`: An optional ID linking this frame to a parent request, workflow task, or stream session.
- `timestamp_ns`: The exact nanosecond epoch when the sender generated the frame.
- `ttl_ms`: The Time-To-Live in milliseconds. If `current_time - timestamp > ttl_ms`, the frame is dropped with an `ERROR` notification (`408 Request Timeout`).
- `sender`: Object containing `agent_id` (`did:acp:...`), `host_id`, `instance_id`, and `pubkey`.
- `receiver`: Object containing `target_type` (`AGENT`, `CLUSTER`, `TOPIC`, `HUMAN`, `TOOL`, `DATABASE`, `ROBOT`, `API`, `BROWSER`), `target_id`, or `routing_query` for skill-based discovery.
- `frame_type`: Enumerated frame purpose (`REQUEST`, `RESPONSE`, `STREAM_CHUNK`, `STREAM_END`, `EVENT`, `NEGOTIATION_PROPOSAL`, `NEGOTIATION_COUNTER`, `NEGOTIATION_ACCEPT`, `NEGOTIATION_REJECT`, `VOTE_CAST`, `TASK_DELEGATION`, `HEARTBEAT`, `ERROR`).
- `routing`: Routing telemetry including `hop_count`, `max_hops`, `reply_to`, `trace_parent` (OpenTelemetry W3C header), and traversed `router_path`.
- `security`: Security credentials including `auth_token`, `capability_token`, cryptographic `signature`, `signature_alg`, `nonce`, and optional `encryption_alg`.
- `payload`: The payload body (JSON object containing action parameters, result data, stream chunks, or voting decisions).

### 5.2 Cryptographic Signing Canonicalization
To prevent tampering across intermediate hops, the sender computes the signature using **Ed25519** (preferred) or **ECDSA-P256** over a deterministic canonical JSON string:
```
CanonicalString = CanonicalJson( acp_version + message_id + timestamp_ns + sender.agent_id + receiver.target_type + receiver.target_id + frame_type + security.nonce + CanonicalJson(payload) )
Signature = Base64Encode( Sign( PrivateKey, SHA256(CanonicalString) ) )
```
When an ACP Gateway or Router receives the frame, it immediately verifies `Signature` against `sender.pubkey` (or the cached DID registry key). If verification fails or `nonce` has been seen within `ttl_ms`, the frame is immediately rejected (`403 Forbidden - Cryptographic Replay or Signature Mismatch`).
