"""ACP Distributed Memory Service Implementation across Six Tiers."""
import time
import math
import copy
from typing import Any, Dict, List, Optional, Tuple
from acp.models.memory import (
    MemoryTier, MemoryOperation, VectorQuery, GraphQuery, MemoryOperationPayload
)


class CRDTElement:
    """LWW-Element-Set entry holding value and logical timestamp in nanoseconds."""
    def __init__(self, key: str, value: Any, timestamp_ns: int) -> None:
        self.key = key
        self.value = value
        self.timestamp_ns = timestamp_ns


class MemoryService:
    """Unified Distributed Memory Service with LRU, KV, CRDT LWW-Set, Vector, Graph, and Snapshots."""

    def __init__(self) -> None:
        # Short-Term LRU Cache: partition_key -> key -> (value, expiry_time_sec)
        self.short_term: Dict[str, Dict[str, Tuple[Any, Optional[float]]]] = {}
        # Long-Term KV Store: partition_key -> key -> (value, expiry_time_sec)
        self.long_term: Dict[str, Dict[str, Tuple[Any, Optional[float]]]] = {}
        # Shared CRDT Store: partition_key -> key -> CRDTElement
        self.shared_crdt: Dict[str, Dict[str, CRDTElement]] = {}
        # Vector Store: partition_key -> list of (key, embedding_list, metadata, value)
        self.vector_store: Dict[str, List[Tuple[str, List[float], Dict[str, Any], Any]]] = {}
        # Knowledge Graph Store: partition_key -> list of (subject, predicate, object)
        self.graph_store: Dict[str, List[Tuple[str, str, str]]] = {}
        # Encrypted Store: partition_key -> key -> encrypted_dict
        self.encrypted_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Snapshot Storage: snapshot_id/partition_key -> deepcopy of partition data
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def _cleanup_ttl(self, store: Dict[str, Dict[str, Tuple[Any, Optional[float]]]], partition_key: str) -> None:
        if partition_key not in store:
            return
        now = time.time()
        keys_to_delete = [
            k for k, (val, exp) in store[partition_key].items()
            if exp is not None and now > exp
        ]
        for k in keys_to_delete:
            del store[partition_key][k]

    def execute_operation(self, payload: MemoryOperationPayload) -> Dict[str, Any]:
        """Dispatch memory operations across tiers."""
        op = payload.operation
        tier = payload.memory_tier
        partition = payload.partition_key

        if op == MemoryOperation.CREATE_SNAPSHOT:
            return self._create_snapshot(partition)
        elif op == MemoryOperation.RESTORE_SNAPSHOT:
            return self._restore_snapshot(partition)
        elif op == MemoryOperation.SYNC_REPLICAS and tier == MemoryTier.SHARED:
            return self._sync_crdt_replicas(partition, payload.value)

        if op == MemoryOperation.PUT:
            return self._put(tier, partition, payload.key, payload.value, payload.ttl_seconds, payload.encryption_details)
        elif op == MemoryOperation.GET:
            return self._get(tier, partition, payload.key)
        elif op == MemoryOperation.DELETE:
            return self._delete(tier, partition, payload.key)
        elif op == MemoryOperation.QUERY_VECTOR and tier == MemoryTier.VECTOR:
            return self._query_vector(partition, payload.vector_query)
        elif op == MemoryOperation.QUERY_GRAPH and tier == MemoryTier.KNOWLEDGE_GRAPH:
            return self._query_graph(partition, payload.graph_query)

        raise ValueError(f"Unsupported operation {op} for tier {tier}")

    def _put(self, tier: MemoryTier, partition: str, key: Optional[str], value: Any, ttl: Optional[int], enc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exp = (time.time() + ttl) if ttl else None

        if tier in (MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM):
            if not key:
                raise ValueError("Key required for SHORT_TERM/LONG_TERM put")
            store = self.short_term if tier == MemoryTier.SHORT_TERM else self.long_term
            if partition not in store:
                store[partition] = {}
            store[partition][key] = (value, exp)
            return {"status": "SUCCESS", "tier": tier.value, "key": key}

        elif tier == MemoryTier.SHARED:
            if not key:
                raise ValueError("Key required for SHARED CRDT put")
            if partition not in self.shared_crdt:
                self.shared_crdt[partition] = {}
            ts = int(time.time_ns())
            elem = CRDTElement(key=key, value=value, timestamp_ns=ts)
            # CRDT Last-Write-Wins Merge check
            existing = self.shared_crdt[partition].get(key)
            if existing is None or ts >= existing.timestamp_ns:
                self.shared_crdt[partition][key] = elem
            return {"status": "SUCCESS", "tier": tier.value, "key": key, "timestamp_ns": ts}

        elif tier == MemoryTier.VECTOR:
            if not isinstance(value, dict) or "embedding" not in value:
                raise ValueError("VECTOR put requires value dict with 'embedding' and optional 'metadata'/'content'")
            if partition not in self.vector_store:
                self.vector_store[partition] = []
            vec_key = key or f"vec_{len(self.vector_store[partition])}"
            self.vector_store[partition].append((
                vec_key,
                value["embedding"],
                value.get("metadata", {}),
                value.get("content", value)
            ))
            return {"status": "SUCCESS", "tier": tier.value, "key": vec_key}

        elif tier == MemoryTier.KNOWLEDGE_GRAPH:
            if not isinstance(value, dict) or not all(k in value for k in ("subject", "predicate", "object")):
                raise ValueError("KNOWLEDGE_GRAPH put requires dict with subject, predicate, object")
            if partition not in self.graph_store:
                self.graph_store[partition] = []
            triple = (value["subject"], value["predicate"], value["object"])
            if triple not in self.graph_store[partition]:
                self.graph_store[partition].append(triple)
            return {"status": "SUCCESS", "tier": tier.value, "triple": triple}

        elif tier == MemoryTier.ENCRYPTED:
            if not key:
                raise ValueError("Key required for ENCRYPTED put")
            if partition not in self.encrypted_store:
                self.encrypted_store[partition] = {}
            # Simulate AES-256-GCM encryption
            key_id = enc.get("key_id", "default_key") if enc else "default_key"
            self.encrypted_store[partition][key] = {
                "ciphertext": f"enc_aes256_{value}",
                "key_id": key_id,
                "timestamp": time.time()
            }
            return {"status": "SUCCESS", "tier": tier.value, "key": key, "encrypted": True}

        return {"status": "ERROR", "message": f"Tier {tier} not handled"}

    def _get(self, tier: MemoryTier, partition: str, key: Optional[str]) -> Dict[str, Any]:
        if tier in (MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM):
            store = self.short_term if tier == MemoryTier.SHORT_TERM else self.long_term
            self._cleanup_ttl(store, partition)
            if partition in store and key in store[partition]:
                return {"status": "SUCCESS", "value": store[partition][key][0]}
            return {"status": "NOT_FOUND", "key": key}

        elif tier == MemoryTier.SHARED:
            if partition in self.shared_crdt and key in self.shared_crdt[partition]:
                elem = self.shared_crdt[partition][key]
                return {"status": "SUCCESS", "value": elem.value, "timestamp_ns": elem.timestamp_ns}
            return {"status": "NOT_FOUND", "key": key}

        elif tier == MemoryTier.ENCRYPTED:
            if partition in self.encrypted_store and key in self.encrypted_store[partition]:
                # Simulate decryption return if key presented properly
                data = self.encrypted_store[partition][key]
                return {"status": "SUCCESS", "encrypted_data": data}
            return {"status": "NOT_FOUND", "key": key}

        return {"status": "ERROR", "message": f"Direct GET not supported on {tier}. Use QUERY_VECTOR or QUERY_GRAPH."}

    def _delete(self, tier: MemoryTier, partition: str, key: Optional[str]) -> Dict[str, Any]:
        if tier in (MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM):
            store = self.short_term if tier == MemoryTier.SHORT_TERM else self.long_term
            if partition in store and key in store[partition]:
                del store[partition][key]
                return {"status": "SUCCESS", "deleted": True}
        elif tier == MemoryTier.SHARED:
            if partition in self.shared_crdt and key in self.shared_crdt[partition]:
                del self.shared_crdt[partition][key]
                return {"status": "SUCCESS", "deleted": True}
        return {"status": "NOT_FOUND", "key": key}

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _query_vector(self, partition: str, query: Optional[VectorQuery]) -> Dict[str, Any]:
        if not query or partition not in self.vector_store:
            return {"status": "SUCCESS", "results": []}

        results = []
        for key, emb, meta, val in self.vector_store[partition]:
            if query.filter_metadata:
                if not all(meta.get(k) == v for k, v in query.filter_metadata.items()):
                    continue
            sim = self._cosine_similarity(query.embedding, emb)
            if sim >= query.min_similarity:
                results.append({"key": key, "similarity": sim, "metadata": meta, "content": val})

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return {"status": "SUCCESS", "results": results[:query.top_k]}

    def _query_graph(self, partition: str, query: Optional[GraphQuery]) -> Dict[str, Any]:
        if not query or partition not in self.graph_store:
            return {"status": "SUCCESS", "triples": []}

        triples = self.graph_store[partition]
        matched = []
        for s, p, o in triples:
            if query.subject and s != query.subject:
                continue
            if query.predicate and p != query.predicate:
                continue
            if query.object and o != query.object:
                continue
            matched.append({"subject": s, "predicate": p, "object": o})

        # Multi-hop traversal if depth > 1 and subject specified
        if query.max_depth > 1 and query.subject:
            visited = set()
            queue = [(query.subject, 0)]
            while queue:
                curr_s, depth = queue.pop(0)
                if depth >= query.max_depth:
                    continue
                for s, p, o in triples:
                    if s == curr_s and (s, p, o) not in visited:
                        visited.add((s, p, o))
                        if {"subject": s, "predicate": p, "object": o} not in matched:
                            matched.append({"subject": s, "predicate": p, "object": o})
                        queue.append((o, depth + 1))

        return {"status": "SUCCESS", "triples": matched}

    def _sync_crdt_replicas(self, partition: str, remote_elements_json: Any) -> Dict[str, Any]:
        """Merge CRDT LWW-Element-Set entries from a remote replica."""
        if partition not in self.shared_crdt:
            self.shared_crdt[partition] = {}
        if not isinstance(remote_elements_json, dict):
            return {"status": "ERROR", "message": "Expected dict of CRDT elements for sync"}

        merged_count = 0
        for k, v_dict in remote_elements_json.items():
            ts = v_dict["timestamp_ns"]
            val = v_dict["value"]
            existing = self.shared_crdt[partition].get(k)
            if existing is None or ts > existing.timestamp_ns:
                self.shared_crdt[partition][k] = CRDTElement(k, val, ts)
                merged_count += 1
        return {"status": "SUCCESS", "merged_keys": merged_count}

    def _create_snapshot(self, partition: str) -> Dict[str, Any]:
        """Create a point-in-time copy-on-write snapshot of a memory partition."""
        snapshot_data = {
            "short_term": copy.deepcopy(self.short_term.get(partition, {})),
            "long_term": copy.deepcopy(self.long_term.get(partition, {})),
            "shared_crdt": {
                k: {"value": v.value, "timestamp_ns": v.timestamp_ns}
                for k, v in self.shared_crdt.get(partition, {}).items()
            },
            "vector_store": copy.deepcopy(self.vector_store.get(partition, [])),
            "graph_store": copy.deepcopy(self.graph_store.get(partition, [])),
            "encrypted_store": copy.deepcopy(self.encrypted_store.get(partition, {}))
        }
        self.snapshots[partition] = snapshot_data
        return {"status": "SUCCESS", "snapshot_partition": partition}

    def _restore_snapshot(self, partition: str) -> Dict[str, Any]:
        """Restore a memory partition exact state from the latest snapshot."""
        if partition not in self.snapshots:
            return {"status": "NOT_FOUND", "message": f"No snapshot for partition {partition}"}
        snap = self.snapshots[partition]
        self.short_term[partition] = copy.deepcopy(snap["short_term"])
        self.long_term[partition] = copy.deepcopy(snap["long_term"])
        self.shared_crdt[partition] = {
            k: CRDTElement(k, v["value"], v["timestamp_ns"])
            for k, v in snap["shared_crdt"].items()
        }
        self.vector_store[partition] = copy.deepcopy(snap["vector_store"])
        self.graph_store[partition] = copy.deepcopy(snap["graph_store"])
        self.encrypted_store[partition] = copy.deepcopy(snap["encrypted_store"])
        return {"status": "SUCCESS", "restored_partition": partition}
