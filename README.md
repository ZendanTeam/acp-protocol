# ACP (Agent Collaboration Protocol) Master Repository & Specification

[![Status: Standards Track](https://img.shields.io/badge/Status-Standards%20Track-brightgreen.svg)]()
[![Specification: RFC-ACP-001..010](https://img.shields.io/badge/RFCs-001%20to%20010-blue.svg)]()
[![JSON Schema: Draft 2020--12](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-orange.svg)]()
[![Reference Runtime: Python 3.13+](https://img.shields.io/badge/Reference%20Runtime-Python%203.13%2B-yellow.svg)]()
[![Tests: 18/18 Passing](https://img.shields.io/badge/pytest-18%2F18%20Passing-success.svg)]()

Welcome to the official master repository for **ACP (Agent Collaboration Protocol)**—the open, cloud-native, transport-agnostic standard designed to serve as the distributed operating protocol and runtime fabric for autonomous AI agents.

---

## 1. Vision & Differentiation: Why Not MCP?

While **Model Context Protocol (MCP)** provides a standardized `1:1` client-to-server mechanism for attaching local tools and prompt context to single application frontends, **ACP** solves the distributed systems challenges that emerge when thousands of autonomous agents must collaborate across heterogeneous clouds, enterprise boundaries, and edge networks (`N:M` topology).

Think of ACP as:
- **Kubernetes for AI Agents:** Orchestration, sandboxed execution, auto-scaling, fault tolerance, and self-healing multi-agent topologies.
- **HTTP + gRPC + OAuth + Event Bus for Autonomous AI:** Unified wire framing, asynchronous streaming, zero-trust cryptographic capability authorization, and publish/subscribe messaging.
- **A Distributed Runtime Rather Than Only a Tool-Calling Protocol:** Distributed memory replication, decentralized peer-to-peer discovery, economic negotiation, multi-agent voting gates, and cryptographic auditability.

---

## 2. Repository & Deliverable Structure

```
acp/
├── README.md                              # Master Overview & Architecture Guide
├── spec/                                  # 10 Complete Production-Grade Specification RFCs
│   ├── 01-architecture-and-vision.md      # RFC-ACP-001: Vision, Principles, Wire Frame Envelope
│   ├── 02-components-and-roles.md         # RFC-ACP-002: Host, Agent, Gateway, Router, Registry...
│   ├── 03-communication-and-transport.md  # RFC-ACP-003: 9 Communication Targets, HTTP3/gRPC/QUIC
│   ├── 04-workflow-and-orchestration.md   # RFC-ACP-004: DAG Workflows, Negotiation, Voting, Rollback
│   ├── 05-distributed-memory.md           # RFC-ACP-005: 6-Tier Memory, CRDT Sync, Vector, KG Triples
│   ├── 06-security-and-zero-trust.md      # RFC-ACP-006: Zero-Trust, DIDs, Capability Tokens, mTLS
│   ├── 07-discovery-and-marketplace.md    # RFC-ACP-007: Gossip Discovery, SLA Match, Marketplace
│   ├── 08-runtime-and-observability.md    # RFC-ACP-008: K8s/Wasm/Edge Runtimes, OpenTelemetry Traces
│   ├── 09-sdk-specifications.md           # RFC-ACP-009: Idiomatic SDK Specs for 14 Languages
│   └── 10-developer-experience-and-migration.md # RFC-ACP-010: CLI, Studio, Debugger, Migration Guide
├── schemas/                               # Official JSON Schemas (Draft 2020-12)
│   ├── envelope.schema.json               # Universal ACP Wire Envelope
│   ├── message.schema.json                # Request, Response, Stream, Negotiation Payloads
│   ├── agent-manifest.schema.json         # Agent Capability & Endpoint Declaration
│   ├── workflow-dag.schema.json           # DAG Execution, Voting Rules, Saga Rollback
│   ├── capability-token.schema.json       # Zero-Trust Signed Access Tokens
│   └── memory-operation.schema.json       # Multi-Tier Distributed Memory Payloads
├── reference-implementation/              # Executable Python Reference Runtime & SDK (`acp-py`)
│   ├── acp/
│   │   ├── models/                        # Pydantic v2 Models (Envelope, Manifest, Workflow, Memory)
│   │   ├── runtime/                       # Host, AgentRuntime, Gateway, Router
│   │   ├── services/                      # Discovery, Registry, Marketplace, Memory Service, IdP
│   │   ├── orchestration/                 # DAG Scheduler, Voting Consensus, Saga Rollback Engine
│   │   ├── transport/                     # Async Event Bus & Broker Abstraction
│   │   └── cli/                           # Interactive Command Line Interface (`acp`)
│   └── tests/                             # Comprehensive pytest Test Suite (100% Passing)
│       ├── test_schemas.py
│       ├── test_envelope_security.py
│       ├── test_memory_service.py
│       ├── test_discovery_marketplace.py
│       └── test_workflow_dag.py
```

---

## 3. Quickstart: Running the Reference Implementation & CLI

You can interact with the live simulated ACP mesh directly using the provided CLI (`acp/cli/main.py`):

### Inspect Live Mesh & Runtimes
```bash
PYTHONPATH=reference-implementation python3 reference-implementation/acp/cli/main.py inspect-mesh
```

### Execute a Multi-Agent DAG Workflow with Voting Gate (`>= 66.7% Consensus`)
```bash
PYTHONPATH=reference-implementation python3 reference-implementation/acp/cli/main.py run-workflow
```

### Simulate Reverse Topological Saga Rollback
```bash
PYTHONPATH=reference-implementation python3 reference-implementation/acp/cli/main.py simulate-saga-rollback
```

### Demonstrate 6-Tier Distributed Memory & CRDT LWW-Element-Set Sync
```bash
PYTHONPATH=reference-implementation python3 reference-implementation/acp/cli/main.py memory-demo
```

### Simulate Protocol-Level Economic SLA Negotiation
```bash
PYTHONPATH=reference-implementation python3 reference-implementation/acp/cli/main.py simulate-negotiation
```

### Run the Automated Test Suite
```bash
PYTHONPATH=reference-implementation pytest reference-implementation/tests/ -v
```

---

## 4. Core Architectural Highlights

1. **Universal Wire Frame Envelope (`envelope.schema.json`):**
   - Transports multi-modal frames (`REQUEST`, `RESPONSE`, `STREAM_CHUNK`, `NEGOTIATION_PROPOSAL`, `VOTE_CAST`) across any transport (HTTP/2/3, QUIC, gRPC, WebSocket, Unix Socket, P2P Mesh).
   - Enforces cryptographic signing over canonical JSON strings (`HMAC-SHA256`, `Ed25519`, `ECDSA`) and time-bounded replay protection using nonces and eviction caches.
2. **Zero-Trust Capability Authorization (`capability-token.schema.json`):**
   - Every agent operates with explicit W3C Decentralized Identifiers (`did:acp:...`).
   - Gateways intercept traffic, verify mTLS certificates, enforce token bucket rate limiting (`1,000 fps`), inject secrets from the Secrets Vault (`secrets://...`), and check granular ABAC claims.
3. **6-Tier Distributed Memory Service (`memory-operation.schema.json`):**
   - **Short-Term (`LRU Cache`):** Sub-millisecond working scratchpad.
   - **Long-Term (`Key-Value`):** Persistent domain entities with auto-expiring TTL.
   - **Shared (`CRDT LWW-Element-Set`):** Lock-free, conflict-free state synchronization where highest logical timestamp deterministically wins across distributed replicas.
   - **Vector (`HNSW Cosine Sim`):** High-dimensional dense embeddings with metadata filtering.
   - **Knowledge Graph (`RDF/LPG Triples`):** Multi-hop relational entity traversal (`Subject -> Predicate -> Object`).
   - **Encrypted (`Enclave Storage`):** Data-at-rest encryption envelopes (`AES-256-GCM`).
4. **DAG Workflow Engine & Saga Rollback (`workflow-dag.schema.json`):**
   - Evaluates complex node dependencies with topological sorting and cycle detection.
   - Dispatches parallel nodes (`PARALLEL_JOIN`) and enforces high-precision consensus via `VOTING_GATE` nodes (`e.g., >= 66.7% weighted approval`).
   - **Saga Pattern Rollback:** If any node fails irrecoverably after `exponential backoff` retries, the Scheduler traverses completed nodes in **reverse topological order**, executing their declared `rollback_action` to restore clean system equilibrium.
