# ACP Developer Experience, Tooling & Migration Specification
**Document Number:** RFC-ACP-010  
**Version:** 1.0.0  

---

## 1. Enterprise Developer Experience (DX) Suite

To ensure rapid onboarding and frictionless daily operations, ACP defines an integrated ecosystem of developer tools:

```
+---------------------------------------------------------------------------------------------------+
|                                      ACP DEVELOPER EXPERIENCE SUITE                               |
|                                                                                                   |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|  |     ACP CLI        |  |     ACP GUI &      |  |  VISUAL WORKFLOW   |  |   DEBUG INSPECTOR   |  |
|  | (`acp run/inspect`)|  |     DASHBOARD      |  |      BUILDER       |  |  (Step/Mock/Trace)  |  |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|            ^                       ^                       ^                        ^             |
|            |                       |                       |                        |             |
|            +-----------------------+-----------+-----------+------------------------+             |
|                                                |                                                  |
|                                                v                                                  |
|                      +---------------------------------------------------+                        |
|                      |             TESTING & SIMULATION ENGINE           |                        |
|                      |       (acp-test, Chaos Monkey, Network Lag Mock)  |                        |
|                      +---------------------------------------------------+                        |
|                                                ^                                                  |
|                                                |                                                  |
|                                                v                                                  |
|                      +---------------------------------------------------+                        |
|                      |          IDE PLUGINS & CODE GENERATORS            |                        |
|                      |  (VS Code, JetBrains, `acp codegen`, Package Mgr) |                        |
|                      +---------------------------------------------------+                        |
+---------------------------------------------------------------------------------------------------+
```

### 1.1 ACP Command Line Interface (`acp`)
The official CLI `acp` is the universal Swiss Army knife for local testing and cluster administration:
- `acp init <template>`: Scaffolds a new agent project (`python`, `ts`, `go`, `rust`) with pre-configured schemas and Dockerfile.
- `acp run <agent.py>`: Spawns the agent inside a local sandboxed ACP Runtime with live reload.
- `acp inspect --did did:acp:org:worker`: Queries the Discovery service and displays real-time capabilities, heartbeats, and memory metrics.
- `acp workflow exec <dag.json>`: Submits a multi-node workflow DAG to the local or cloud Scheduler and streams execution logs.
- `acp memory query --tier VECTOR --query "quarterly revenue"`: Queries local or remote vector memory directly from terminal.
- `acp validate <envelope.json>`: Validates payloads against official JSON schemas (`draft-2020-12`).

### 1.2 GUI, Dashboard & Visual Workflow Builder
- **Dashboard (`http://localhost:8080`):** Interactive web interface providing real-time node topology, token consumption graphs, and cost attribution per agent DID.
- **Visual Workflow Builder (`ACP Studio`):** Drag-and-drop canvas where developers wire agents together, configure task delegation lines, set voting thresholds (`>= 66%`), and export clean `workflow-dag.schema.json` files without writing boilerplate JSON by hand.

### 1.3 Debug Mode & Protocol Inspector
- **Interactive Step Debugging:** When launched with `acp run --debug`, the local Gateway intercepts every envelope, allowing developers to set breakpoints on frame arrival, inspect capability claims, modify parameters on the fly, and step through DAG nodes one by one.
- **Protocol Inspector:** Captures and decodes canonical signature strings, verifying exact `SHA-256` payload hashes and displaying exact verification traces when cryptographic signatures fail.

### 1.4 Testing Framework (`acp-test`) & Simulation Environment
- **Unit & Integration Testing:** Developers write declarative mock fixtures (`mock_peer.json`) specifying exact response frames. `acp-test` runs the agent against simulated mesh peers without needing real API keys or expensive LLM token consumption.
- **Chaos & Network Simulation Engine:** Simulates real-world distributed mesh hazards:
  - `Latency Injection`: Adds `200ms - 5,000ms` random jitter to test SLA renegotiation.
  - `Packet Drop / Replay`: Drops `10%` of frames or retransmits old nonces to test cryptographic replay defense.
  - `Node Crash / Partition`: Kills parallel worker agents mid-execution to verify automatic checkpoint recovery and `rollback_action` execution.

### 1.5 Package Manager (`acpm`) & Code Generator (`acp codegen`)
- **Package Manager (`acpm install skill/sql-optimizer@1.2.0`):** Pulls verified OCI skill packages and prompt templates from the ACP Marketplace directly into the local project workspace (`./acp_modules/`).
- **Code Generator (`acp codegen --schema agent-manifest.json --lang python`):** Generates strongly typed client stubs, Pydantic/Zod models, and skill handlers directly from JSON Schema definitions.

### 1.6 IDE Extensions (`VS Code` & `JetBrains`)
- Live JSON Schema validation and autocompletion for `envelope.schema.json` and `workflow-dag.schema.json`.
- Inline CodeLens showing real-time agent cost estimates (`Estimated cost: 1.5 credits/call`) and hover preview of skill input/output schemas.

---

## 2. Comprehensive Migration Guides

### 2.1 Migrating from Model Context Protocol (`MCP`) to ACP
- **Context Attachment vs. Mesh Collaboration:** Keep using your existing MCP servers (`stdio`/SSE) to feed prompt context into your local IDE frontend (`1:1`). When your agent needs to delegate a task to a remote team worker or query a distributed vector memory tier across machines, wrap the call using an ACP Client envelope (`ACPClient.sendRequest()`).
- **Tool Mapping:** Convert MCP `tools/list` handlers into ACP `Skill` registrations (`client.registerSkill()`). ACP Gateways will automatically handle authentication (`OIDC`/`CapabilityToken`) and rate limiting that MCP left to the client loop.

### 2.2 Migrating from LangGraph / CrewAI / AutoGPT to ACP Workflows
- **Replacing Python/Local State Loops:** Instead of running in-memory Python `while True:` agent loops that crash when memory runs out or host reboots occur, export your agent nodes as independent microservices or containerized ACP agents.
- **Converting Graphs to DAGs:** Map LangGraph conditional edges directly into `workflow-dag.schema.json` nodes with explicit `dependencies`. Replace in-memory python variable sharing with calls to the **ACP Memory Service (`SHARED` tier with CRDTs)**.

---

## 3. Best Practices & Security Checklist

1. **Always Set Granular Capability Tokens:** Never issue wildcard capabilities (`*/*`) in production. Restrict tokens to exact target DIDs, resource namespaces, and invocation limits (`max_invocations`).
2. **Implement Rollback Actions (`rollback_action`):** Every mutating workflow node (e.g., database insert, cloud resource creation) MUST declare a corresponding rollback skill to guarantee clean Saga recovery on failure.
3. **Use Vector Indexing for Dynamic Discovery:** Instead of hardcoding target `did` strings in DAGs, use `target_skill_query` with semantic requirements (`{"skill": "code review", "max_cost_credits": 3.0}`) so the Router can automatically select the most cost-effective and responsive peer agent available on the mesh.
4. **Enable End-to-End Encryption (`E2EE`) across Semi-Trusted Brokers:** If message envelopes traverse third-party cloud brokers or public event buses, set `security.encryption_alg = "AES-256-GCM"` and encrypt payload keys using HPKE.
