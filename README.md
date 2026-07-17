# ACP (Agent Collaboration Protocol) Master Repository & Package Ecosystem

[![Status: Standards Track](https://img.shields.io/badge/Status-Standards%20Track-brightgreen.svg)]()
[![Specification: RFC-ACP-001..010](https://img.shields.io/badge/RFCs-001%20to%20010-blue.svg)]()
[![JSON Schema: Draft 2020--12](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-orange.svg)]()
[![Reference Runtime: Python 3.13+](https://img.shields.io/badge/Reference%20Runtime-Python%203.13%2B-yellow.svg)]()
[![Tests: 18/18 Passing](https://img.shields.io/badge/pytest-18%2F18%20Passing-success.svg)]()
[![Release v1.0.0](https://img.shields.io/badge/Release-v1.0.0-gold.svg)](https://github.com/ZendanTeam/acp-protocol/releases/tag/v1.0.0)

Welcome to the official master repository for **ACP (Agent Collaboration Protocol)**—the open, cloud-native, transport-agnostic standard designed to serve as the distributed operating protocol and runtime fabric for autonomous AI agents (`N:M` mesh collaboration).

---

## 📦 Quick Installation & Package Ecosystem

We have built full distribution packages, Docker images, and SDKs so you don't have to manually manage source code:

### 1. Python Package (`wheel` & `sdist`)
Install the official Python reference runtime and CLI directly from our release artifacts or locally:
```bash
# Install pre-built Wheel directly from GitHub Release v1.0.0
pip install https://github.com/ZendanTeam/acp-protocol/releases/download/v1.0.0/acp_protocol-1.0.0-py3-none-any.whl

# Or install from source
git clone https://github.com/ZendanTeam/acp-protocol.git
cd acp-protocol
pip install .
```
Once installed, the `acp` command is available globally on your terminal!

### 2. TypeScript & Node.js SDK (`@acp-protocol/sdk`)
For frontend, Node.js, Next.js, or browser Web Worker agents:
```bash
cd sdk/typescript
npm install
npm run build
```

### 3. Docker & Docker Compose
Launch a complete sandboxed ACP Node (`Gateway` + `Router` + `Memory Service` + `Dashboard`) locally or in production:
```bash
docker compose up -d
```

---

## 🚀 Interactive CLI Commands (`acp`)

After installing via `pip`, you can run all 5 interactive protocol verification commands directly:

```bash
# 1. Inspect the live mesh topology and registered agent manifests
acp inspect-mesh

# 2. Execute a multi-agent DAG workflow with a Voting Gate (>= 66.7% consensus)
acp run-workflow

# 3. Simulate unrecoverable node failure and reverse Saga Rollback
acp simulate-saga-rollback

# 4. Demonstrate the 6-Tier Distributed Memory & CRDT LWW-Element-Set Sync
acp memory-demo

# 5. Simulate protocol-level economic SLA negotiation (PROPOSE -> COUNTER -> ACCEPT)
acp simulate-negotiation
```

---

## 🏗️ Automated CI/CD & GitHub Actions (`.github/workflows/`)

This repository is backed by complete, production-ready continuous integration and deployment pipelines:
- **`ci.yml`**: Runs the 18-test `pytest` verification suite across Python `3.10`, `3.11`, `3.12`, and `3.13`, validates all 6 JSON Schemas (`draft-2020-12`), and builds the TypeScript SDK on every push and pull request.
- **`release.yml`**: Automatically builds Python Wheels (`.whl`), builds and pushes multi-stage Docker container images (`ghcr.io/ZendanTeam/acp-protocol:latest`), and publishes release assets to GitHub Releases upon every version tag push (`v*`).

---

## 📚 Protocol Specification Directory (`spec/`)

1. [`01-architecture-and-vision.md`](./spec/01-architecture-and-vision.md) — **RFC-ACP-001:** Vision, Core Principles, Mesh Topology, and Universal Envelope Canonicalization (`Ed25519`/`HMAC-SHA256`).
2. [`02-components-and-roles.md`](./spec/02-components-and-roles.md) — **RFC-ACP-002:** Deep-dive specifications for all 15 components: *Host, Agent, Gateway, Router, Registry, Discovery, Memory Service, Scheduler, Broker, Identity Provider (IdP), Marketplace, Runtime, Monitoring, Logging, and Telemetry*.
3. [`03-communication-and-transport.md`](./spec/03-communication-and-transport.md) — **RFC-ACP-003:** Semantics for the 9 communication vectors (*Agent→Agent, Human, Tool, Database, API, Browser, Robot, Cluster, Cloud*), transport bindings (*HTTP/1/2/3, QUIC, gRPC, WebSocket, Unix Socket, TCP, UDP, Bluetooth, mDNS, P2P Mesh*), and native multi-modal streaming.
4. [`04-workflow-and-orchestration.md`](./spec/04-workflow-and-orchestration.md) — **RFC-ACP-004:** DAG execution rules, task delegation, planning, SLA negotiation (`PROPOSE`→`COUNTER`→`ACCEPT`), voting consensus gates (`VOTING_GATE`), exponential backoff retries, checkpoint snapshots, and **reverse topological Saga Rollbacks (`rollback_action`)**.
5. [`05-distributed-memory.md`](./spec/05-distributed-memory.md) — **RFC-ACP-005:** Unified 6-tier distributed memory (*Short-Term LRU, Long-Term KV, Shared CRDT LWW-Element-Set, Vector Cosine Sim, Knowledge Graph RDF/LPG Triples, Encrypted Enclaves*), replication loops, and copy-on-write snapshots.
6. [`06-security-and-zero-trust.md`](./spec/06-security-and-zero-trust.md) — **RFC-ACP-006:** Zero-Trust request lifecycle, OAuth2/OIDC token exchange (`RFC 8693`), mutual TLS (`mTLS 1.3/QUIC`), cryptographic capability tokens, ABAC claims, replay eviction caches (`message_id + nonce`), token bucket rate limiting (`1,000 fps`), and the automated **Secrets Vault**.
7. [`07-discovery-and-marketplace.md`](./spec/07-discovery-and-marketplace.md) — **RFC-ACP-007:** Multi-tier discovery (`mDNS` + `SWIM Gossip` + `Registry Queries`), semantic vector skill matching, and the ACP Marketplace catalog for verified *Skills, Plugins, Tools, Models, Workflows, Templates, and Knowledge Packs*.
8. [`08-runtime-and-observability.md`](./spec/08-runtime-and-observability.md) — **RFC-ACP-008:** Runtime targets across *Docker, K8s, Serverless (Lambda/Workers), Bare Metal (cgroups v2), Edge/IoT (Micro-ROS), Mobile/Desktop, and Browser (Wasm Web Workers)*, and OpenTelemetry (`traceparent: 00-4bf92f35...-01`) metrics and circuit breakers.
9. [`09-sdk-specifications.md`](./spec/09-sdk-specifications.md) — **RFC-ACP-009:** Architectural layers, client abstractions, and idiomatic code signatures across **14 programming languages** (`Go`, `Rust`, `C#`, `Java`, `Kotlin`, `Swift`, `Python`, `JavaScript`, `TypeScript`, `PHP`, `Ruby`, `Lua`, `C`, `C++`).
10. [`10-developer-experience-and-migration.md`](./spec/10-developer-experience-and-migration.md) — **RFC-ACP-010:** CLI (`acp`), GUI Dashboard, Visual Studio Workflow Builder, step debugger, chaos simulation (`acp-test`), code generator (`acp codegen`), and complete migration guides from **MCP**, **LangGraph**, **CrewAI**, and **AutoGPT**.

---

## 📋 Formal JSON Schemas (`schemas/`)

All wire payloads are formalized using `draft-2020-12` JSON Schemas:
- [`envelope.schema.json`](./schemas/envelope.schema.json) — Universal ACP Frame Envelope (routing headers, W3C traceparent, signatures, capability tokens, nonces, payload bodies).
- [`message.schema.json`](./schemas/message.schema.json) — Payloads for `REQUEST`, `RESPONSE`, `STREAM_CHUNK`, `NEGOTIATION_PROPOSAL`, `VOTE_CAST`, and `TASK_DELEGATION`.
- [`agent-manifest.schema.json`](./schemas/agent-manifest.schema.json) — Manifest published to Registry (`did:acp:...`, skills, endpoints, compute requirements, security profiles).
- [`workflow-dag.schema.json`](./schemas/workflow-dag.schema.json) — Directed Acyclic Graph specification, nodes, dependencies, voting consensus gates, and `rollback_action` declarations.
- [`capability-token.schema.json`](./schemas/capability-token.schema.json) — Cryptographically signed zero-trust token granting time-bound action rights over resource URI patterns.
- [`memory-operation.schema.json`](./schemas/memory-operation.schema.json) — Operations for reading, writing, vector querying (`min_similarity`), graph querying (`max_depth`), CRDT syncing, and snapshotting across the 6 memory tiers.
