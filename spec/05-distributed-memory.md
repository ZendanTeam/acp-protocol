# ACP Distributed Memory Specification
**Document Number:** RFC-ACP-005  
**Version:** 1.0.0  

---

## 1. Unified Six-Tier Memory Architecture

In traditional AI applications, memory is fragmented across local variables, one-off vector databases, and ad-hoc SQL tables. The **ACP Memory Service** provides a unified, distributed, multi-tier memory fabric that allows agents to read, write, query, and synchronize state across the entire mesh using a standardized payload schema (`memory-operation.schema.json`).

```
+---------------------------------------------------------------------------------------------------+
|                                     ACP DISTRIBUTED MEMORY SERVICE                                |
|                                                                                                   |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|  |  SHORT-TERM LRU    |  |   LONG-TERM KV     |  |   SHARED STATE     |  |    VECTOR INDEX     |  |
|  |  (Volatile RAM)    |  |  (Persistent Disk) |  |   (CRDT / Pub-Sub) |  |  (Cosine/L2 Embed)  |  |
|  |  [SLA < 1ms]       |  |  [SLA < 10ms]      |  |   [SLA < 5ms]      |  |  [SLA < 25ms]       |  |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|            ^                       ^                       ^                        ^             |
|            |                       |                       |                        |             |
|            +-----------------------+-----------+-----------+------------------------+             |
|                                                |                                                  |
|                                                v                                                  |
|                      +---------------------------------------------------+                        |
|                      |             KNOWLEDGE GRAPH TRIPLES               |                        |
|                      |           (RDF / Labeled Property Graph)          |                        |
|                      |                   [SLA < 30ms]                    |                        |
|                      +---------------------------------------------------+                        |
|                                                ^                                                  |
|                                                |                                                  |
|                                                v                                                  |
|                      +---------------------------------------------------+                        |
|                      |              ENCRYPTED SECURE ENCLAVE             |                        |
|                      |              (AES-256-GCM / KMS Keys)             |                        |
|                      |                   [SLA < 15ms]                    |                        |
|                      +---------------------------------------------------+                        |
+---------------------------------------------------------------------------------------------------+
|   REPLICATION PLANE: Multi-Master CRDTs (State Sync) & Raft Consensus (Metadata / Snapshots)      |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Memory Tiers Deep-Dive

### 2.1 Short-Term Memory (`SHORT_TERM`)
- **Semantic Role:** High-speed working memory for intermediate calculation states, transient prompt scratchpads, and active session history.
- **Storage Backend:** In-memory LRU (Least Recently Used) cache backed by Redis or local `ConcurrentHashMap`.
- **Latency & Eviction:** Sub-millisecond latency (`<1ms`). Automatically evicted when memory thresholds exceed 90% or upon session termination (`partition_key = session_id`).

### 2.2 Long-Term Memory (`LONG_TERM`)
- **Semantic Role:** Persistent storage for user preferences, historical agent execution logs, and durable domain entities.
- **Storage Backend:** Distributed Key-Value store backed by RocksDB or Amazon DynamoDB.
- **Latency & Durability:** Low latency (`<10ms`). Strongly durable; written to disk and replicated across at least three physical availability zones (`RF=3`).

### 2.3 Shared Memory (`SHARED`)
- **Semantic Role:** Collaborative workspace memory synchronized in real-time between multiple agents operating concurrently on the same task or DAG.
- **Storage Backend & Sync Pattern:** Implemented using **Conflict-Free Replicated Data Types (`CRDTs`)**—specifically **LWW-Element-Set (Last-Write-Wins Element Set)** and **PN-Counters**.
- **Conflict Free Guarantee:** If two agents write to the exact same key in `SHARED` memory concurrently, the entry with the highest logical timestamp (`timestamp_ns`) deterministically wins across all replicas without requiring distributed locks or blocking consensus rounds.

### 2.4 Vector Memory (`VECTOR`)
- **Semantic Role:** Semantic search and retrieval-augmented generation (`RAG`) storage for dense high-dimensional embeddings generated by vision and language models.
- **Storage Backend:** Hierarchical Navigable Small World (`HNSW`) graph index supporting Cosine Similarity, Inner Product, and Euclidean ($L_2$) distance metrics.
- **Query Operation (`QUERY_VECTOR`):** Agents query vector memory by submitting an query embedding vector (`vector_query.embedding`), `top_k`, `min_similarity`, and metadata filters (`vector_query.filter_metadata: {"domain": "finance", "year": 2026}`).

### 2.5 Knowledge Graph Memory (`KNOWLEDGE_GRAPH`)
- **Semantic Role:** Structured relational reasoning over entity networks, rules, taxonomies, and causal dependencies.
- **Storage Backend:** Resource Description Framework (`RDF`) and Labeled Property Graph triple store (`Subject -> Predicate -> Object`).
- **Query Operation (`QUERY_GRAPH`):** Agents traverse entity relationships up to `max_depth` (e.g., query `Subject: "Agent Alpha"`, `Predicate: "delegated_to"`, retrieving all child nodes up to 3 hops away).

### 2.6 Encrypted Memory (`ENCRYPTED`)
- **Semantic Role:** Secure storage for sensitive PII, healthcare records (`HIPAA`), proprietary source code, and cryptographic credentials.
- **Storage Backend:** Data-at-rest encryption envelope using **AES-256-GCM** or **ChaCha20-Poly1305**.
- **Zero-Trust Access Control:** Encrypted memory partitions cannot be read even by the ACP Host admin or underlying storage infrastructure. Only agents possessing a valid **Capability Token** (`capability-token.schema.json`) with cryptographic decryption rights (`encryption_details.key_id`) can obtain the ephemeral decryption key via the Secrets Vault (`mTLS`).

---

## 3. Distributed Lifecycle & Synchronization Mechanisms

### 3.1 Memory Replication & Synchronization (`SYNC_REPLICAS`)
To maintain consistency across geographically distributed ACP clusters without central bottlenecks, the Memory Service operates two synchronization loops:
- **Asynchronous Gossip Replication:** Short-Term, Long-Term, and Vector updates are broadcast asynchronously across peer nodes using Epidemic Gossip (`gossip interval: 100ms`), achieving eventual consistency with sub-second convergence.
- **CRDT State Merging:** Whenever an agent performs a `PUT` or `SYNC_REPLICAS` operation on `SHARED` memory, the local Memory Service computes the delta state vector and merges it directly into peer memory partitions.

### 3.2 Time-To-Live (`TTL`) Expiration
Every memory entry can optionally specify `ttl_seconds` (e.g., `ttl_seconds: 3600` for 1 hour).
- The Memory Service maintains a priority queue of expiration timestamps.
- When `current_time >= entry.timestamp + ttl_seconds`, a background sweeper thread marks the entry as expired (`Tombstone`), purging it from local disk and broadcasting an eviction event to peer replicas during the next gossip cycle.

### 3.3 Memory Snapshots (`CREATE_SNAPSHOT` / `RESTORE_SNAPSHOT`)
Point-in-time durability is achieved through immutable memory snapshots:
- When triggered by an agent (`operation: CREATE_SNAPSHOT`) or by the Scheduler after completing a workflow DAG checkpoint, the Memory Service performs a copy-on-write (`CoW`) serialization of all memory entries under the specified `partition_key`.
- Snapshots are compressed using `Zstandard (zstd)`, SHA-256 hashed for integrity verification, and persisted to durable object storage (`s3://acp-snapshots/partition-xyz-v1.tar.zst`).
- If an agent or workflow requires rollback, issuing `operation: RESTORE_SNAPSHOT` instantly reverts the entire distributed memory partition to the exact state captured at snapshot creation time.
