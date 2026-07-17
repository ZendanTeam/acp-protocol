"""Tests for the 6-Tier Distributed Memory Service."""
import time
import pytest
from acp.services.memory import MemoryService, MemoryTier, MemoryOperation, MemoryOperationPayload, VectorQuery, GraphQuery


def test_short_and_long_term_memory():
    mem = MemoryService()
    
    # Put short term
    res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.SHORT_TERM,
        partition_key="sess_101",
        key="temp_key",
        value={"foo": "bar"},
        ttl_seconds=3600
    ))
    assert res["status"] == "SUCCESS"
    
    # Get short term
    get_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET,
        memory_tier=MemoryTier.SHORT_TERM,
        partition_key="sess_101",
        key="temp_key"
    ))
    assert get_res["status"] == "SUCCESS"
    assert get_res["value"] == {"foo": "bar"}


def test_shared_crdt_memory():
    mem = MemoryService()
    
    # Put initial CRDT element
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.SHARED,
        partition_key="crdt_part",
        key="counter_val",
        value=10
    ))
    
    # Sync with remote replica with higher timestamp
    higher_ts = int(time.time_ns()) + 1_000_000
    remote_data = {
        "counter_val": {"timestamp_ns": higher_ts, "value": 42}
    }
    sync_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.SYNC_REPLICAS,
        memory_tier=MemoryTier.SHARED,
        partition_key="crdt_part",
        value=remote_data
    ))
    assert sync_res["status"] == "SUCCESS"
    
    get_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET,
        memory_tier=MemoryTier.SHARED,
        partition_key="crdt_part",
        key="counter_val"
    ))
    assert get_res["value"] == 42


def test_vector_cosine_similarity():
    mem = MemoryService()
    
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.VECTOR,
        partition_key="vec_space",
        key="doc_1",
        value={"embedding": [1.0, 0.0, 0.0], "metadata": {"tag": "A"}, "content": "Exact match vector"}
    ))
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.VECTOR,
        partition_key="vec_space",
        key="doc_2",
        value={"embedding": [0.0, 1.0, 0.0], "metadata": {"tag": "B"}, "content": "Orthogonal vector"}
    ))
    
    # Query vector [0.99, 0.1, 0.0]
    query_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.QUERY_VECTOR,
        memory_tier=MemoryTier.VECTOR,
        partition_key="vec_space",
        vector_query=VectorQuery(embedding=[0.99, 0.1, 0.0], top_k=2, min_similarity=0.5)
    ))
    assert len(query_res["results"]) == 1
    assert query_res["results"][0]["key"] == "doc_1"


def test_knowledge_graph():
    mem = MemoryService()
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.KNOWLEDGE_GRAPH,
        partition_key="kg_space",
        value={"subject": "Agent Alpha", "predicate": "delegated_to", "object": "Agent Beta"}
    ))
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.KNOWLEDGE_GRAPH,
        partition_key="kg_space",
        value={"subject": "Agent Beta", "predicate": "delegated_to", "object": "Agent Gamma"}
    ))
    
    # Multi-hop query depth 2
    query_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.QUERY_GRAPH,
        memory_tier=MemoryTier.KNOWLEDGE_GRAPH,
        partition_key="kg_space",
        graph_query=GraphQuery(subject="Agent Alpha", max_depth=2)
    ))
    assert len(query_res["triples"]) == 2


def test_snapshots():
    mem = MemoryService()
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.LONG_TERM,
        partition_key="snap_part",
        key="foo",
        value="bar"
    ))
    
    # Create snapshot
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.CREATE_SNAPSHOT,
        memory_tier=MemoryTier.LONG_TERM,
        partition_key="snap_part"
    ))
    
    # Mutate state
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT,
        memory_tier=MemoryTier.LONG_TERM,
        partition_key="snap_part",
        key="foo",
        value="mutated_value"
    ))
    
    # Restore snapshot
    mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.RESTORE_SNAPSHOT,
        memory_tier=MemoryTier.LONG_TERM,
        partition_key="snap_part"
    ))
    
    get_res = mem.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET,
        memory_tier=MemoryTier.LONG_TERM,
        partition_key="snap_part",
        key="foo"
    ))
    assert get_res["value"] == "bar"
