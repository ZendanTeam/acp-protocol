"""Distributed Memory Operation Models."""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"
    SHARED = "SHARED"
    VECTOR = "VECTOR"
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    ENCRYPTED = "ENCRYPTED"


class MemoryOperation(str, Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"
    QUERY_VECTOR = "QUERY_VECTOR"
    QUERY_GRAPH = "QUERY_GRAPH"
    SYNC_REPLICAS = "SYNC_REPLICAS"
    CREATE_SNAPSHOT = "CREATE_SNAPSHOT"
    RESTORE_SNAPSHOT = "RESTORE_SNAPSHOT"


class VectorQuery(BaseModel):
    embedding: List[float] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1)
    min_similarity: float = Field(default=0.75, ge=0.0, le=1.0)
    filter_metadata: Optional[Dict[str, Any]] = None


class GraphQuery(BaseModel):
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    max_depth: int = Field(default=2, ge=1, le=10)


class MemoryOperationPayload(BaseModel):
    operation: MemoryOperation
    memory_tier: MemoryTier
    partition_key: str
    key: Optional[str] = None
    value: Optional[Union[str, Dict[str, Any], List[Any], float, int, bool]] = None
    ttl_seconds: Optional[int] = None
    vector_query: Optional[VectorQuery] = None
    graph_query: Optional[GraphQuery] = None
    encryption_details: Optional[Dict[str, Any]] = None
