# ACP Discovery & Marketplace Specification
**Document Number:** RFC-ACP-007  
**Version:** 1.0.0  

---

## 1. Multi-Modal Discovery Engine

In a dynamic, decentralized AI mesh, agents cannot rely on static configuration files or hardcoded endpoints. The **ACP Discovery Service** enables autonomous agents to dynamically query and locate optimal peers based on capabilities, current compute availability, geographic latency SLAs, and real-time economic cost.

```
+---------------------------------------------------------------------------------------------------+
|                                     ACP MULTI-TIER DISCOVERY                                      |
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  | TIER 1: LOCAL NETWORK DISCOVERY (mDNS / DNS-SD on UDP port 5353: _acp._tcp.local.)          |  |
|  | -> Instant zero-config peer discovery for edge robots, IoT devices, and local developer PCs. |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                ^                                                  |
|                                                |                                                  |
|                                                v                                                  |
|  +---------------------------------------------------------------------------------------------+  |
|  | TIER 2: CLUSTER GOSSIP & MESH DISCOVERY (SWIM / Serf Gossip Protocol over UDP/TCP)          |  |
|  | -> Decentralized topology mapping, heartbeats, compute metrics, and dynamic routing tables. |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                ^                                                  |
|                                                |                                                  |
|                                                v                                                  |
|  +---------------------------------------------------------------------------------------------+  |
|  | TIER 3: GLOBAL REGISTRY & DISCOVERY SERVICE (/acp/v1/discovery/query via gRPC/HTTP2)        |  |
|  | -> Rich semantic queries across millions of registered manifests, vector indexing of skills.|  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Discovery Query & Matching Semantics

An agent needing to delegate a task issues a **Skill-Based Discovery Query** (`receiver.routing_query`) or invokes the Discovery Service endpoint directly (`/acp/v1/discovery/query`).

### 2.1 Discoverable Entity Attributes
The Discovery Service indexes eleven distinct dimensions from published `agent-manifest.schema.json` registrations:
1. **Capabilities & Skills:** Semantic description and exact JSON schema of supported skills (`skill_id: "sql_query_optimizer"`).
2. **Models:** Underlying LLM or vision foundation models (`provider: "Anthropic", model_id: "claude-3-5-sonnet"` or `provider: "Local", model_id: "llama-3-70b"`).
3. **Resources & Compute Availability:** Live hardware capacity (`min_cpu_cores`, `min_ram_mb`, `gpu_required: true`, current GPU VRAM utilization percentage).
4. **Tools:** List of attached atomic tools and sandboxed execution runtimes (`tools: ["python_sandbox", "web_scraper", "github_cli"]`).
5. **Permissions & Security Profile:** Supported authentication schemes (`OIDC`, `mTLS`, `CAPABILITY_TOKEN`) and sandbox isolation level (`CONTAINER`, `WASM`, `VM`).
6. **Nearby Agents & Latency (`Network SLA`):** Network hop distance and historical ping latencies between source and target hosts (`SLA < 50ms`).
7. **Clusters:** Available cloud and edge cluster pools (`cluster_id: "us-east-gpu-pool"`).
8. **Memory Providers:** Available distributed memory partitions and persistence SLAs (`memory_tier: "VECTOR"` or `"KNOWLEDGE_GRAPH"`).
9. **Vector Stores:** Specialized dense retrieval endpoints (`hnsw_index: "medical_records_768d"`).
10. **Cost & Economic Metrics:** Cost per invocation in standardized credits (`cost_credits_per_invocation: 2.5`).
11. **Reputation & Reliability Scores:** Historical success percentage and SLA compliance rating (`reliability_score: 0.998` across 50,000 completed tasks).

### 2.2 Semantic Vector Skill Discovery
To allow agents to discover relevant skills even when exact `skill_id` strings do not match (e.g., querying for `"analyze quarterly financial spreadsheet"` when the registered skill is `"excel_revenue_forecasting"`), the Discovery Service embeds skill descriptions into a dense vector index (`HNSW`).
- The query string is vectorized (`768-dimensional embedding`).
- The Discovery Service performs a hybrid search: Cosine Similarity matching (`score >= 0.82`) combined with hard filtering on required security profiles and maximum cost budgets.

---

## 3. The ACP Marketplace Architecture

The **ACP Marketplace** is the authoritative enterprise and community registry for publishing, discovering, verifying, and deploying agent artifacts.

```
+---------------------------------------------------------------------------------------------------+
|                                      ACP MARKETPLACE CATALOG                                      |
|                                                                                                   |
|  +-------------------+  +-------------------+  +-------------------+  +------------------------+  |
|  |      SKILLS       |  |      PLUGINS      |  |       TOOLS       |  |         MODELS         |  |
|  | (JSON Schemas +   |  | (Wasm / Python    |  | (Atomic Binary /  |  | (GGUF / Safetensors /  |  |
|  |  Prompt Templates)|  |  Container Logic) |  |  API Wrappers)    |  |  LoRA Adapter Weights) |  |
|  +-------------------+  +-------------------+  +-------------------+  +------------------------+  |
|            ^                      ^                      ^                         ^              |
|            |                      |                      |                         |              |
|            +----------------------+----------+-----------+-------------------------+              |
|                                              |                                                    |
|                                              v                                                    |
|                      +-----------------------------------------------+                            |
|                      |             WORKFLOWS & TEMPLATES             |                            |
|                      |         (Complete Multi-Node DAG Files)       |                            |
|                      +-----------------------------------------------+                            |
|                                              ^                                                    |
|                                              |                                                    |
|                                              v                                                    |
|                      +-----------------------------------------------+                            |
|                      |                KNOWLEDGE PACKS                |                            |
|                      |  (Pre-indexed Vector Embeddings & RDF Triples)|                            |
|                      +-----------------------------------------------+                            |
+---------------------------------------------------------------------------------------------------+
|        SECURITY & GOVERNANCE PLANE: Automated Static Analysis, Wasm Verification & Sig Check     |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Marketplace Artifact Types
1. **Skills:** Declarative JSON schema definitions defining inputs, outputs, natural language instructions, and error codes.
2. **Plugins:** Self-contained executable bundles compiled to WebAssembly (`WASI`) or packaged as OCI containers that extend agent processing capabilities.
3. **Tools:** Atomic executable tools that interface with external APIs, databases, or local host utilities under strict capability sandboxes.
4. **Models:** Fine-tuned model weights, LoRA adapters (`.safetensors`), and quantization parameters optimized for edge and cloud deployment.
5. **Workflows & Templates:** Complete multi-agent DAG execution specifications (`workflow-dag.schema.json`) pre-configured with node relationships, voting rules, and fallback strategies.
6. **Knowledge Packs:** Pre-compiled domain intelligence bundles containing dense vector indexes (`.index` files) and Knowledge Graph RDF/LPG triple dumps ready for instant ingestion into an agent's Memory Service (`e.g., Legal Taxonomy Pack v2026`).

### 3.2 Security Verification & Publishing Pipeline
To protect enterprises from malicious code injections or trojanized prompts, the Marketplace enforces a rigorous automated verification pipeline before any artifact is published:
1. **Cryptographic Publisher Signature:** The publisher signs the artifact bundle using their private key (`Ed25519`). The Marketplace verifies the signature against the publisher's verified DID identity.
2. **Automated Static & Dynamic Vulnerability Analysis:** Wasm binaries and container images undergo deep static analysis (`AST inspection`, `Memory safety checks`, `Dependency vulnerability scanning via Trivy/Snyk`).
3. **Sandbox Behavioral Execution:** The plugin is executed within a high-security Wasm/Firecracker detonation sandbox where its network requests and file system operations are monitored. If the plugin attempts unauthorized network connections or reads outside declared manifest capabilities, publishing is immediately blocked (`STATUS: REJECTED - Malicious Capability Violation`).
4. **Immutable OCI Artifact Generation:** Verified packages are stored as immutable Open Container Initiative (`OCI`) artifacts (`acp://registry.acp.protocol.org/skills/sql_optimizer:v1.2.0`) with SHA-256 content-addressable digests to guarantee deterministic installations.
