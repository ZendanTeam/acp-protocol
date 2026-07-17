"""Specific Payload Models embedded inside ACP Envelopes."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class RequestPayload(BaseModel):
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(default=30000)
    stream_requested: bool = False


class ResponsePayload(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, ERROR, PENDING, REJECTED, ACCEPTED
    status_code: int = 200
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class StreamChunkPayload(BaseModel):
    stream_id: str
    sequence_number: int = Field(..., ge=0)
    content_type: str = "text/plain"
    data: Union[str, Dict[str, Any], List[Any]]
    is_final: bool = False


class NegotiationProposalTerms(BaseModel):
    price_credits: float = Field(..., ge=0.0)
    sla_max_latency_ms: int
    required_capabilities: List[str] = Field(default_factory=list)
    expiry_timestamp_ns: Optional[int] = None


class NegotiationPayload(BaseModel):
    negotiation_id: str
    phase: str  # PROPOSE, COUNTER, ACCEPT, REJECT
    proposal_terms: Optional[NegotiationProposalTerms] = None
    counter_reason: Optional[str] = None


class VotePayload(BaseModel):
    voting_session_id: str
    voter_id: str
    decision: str  # APPROVE, REJECT, ABSTAIN
    weight: float = Field(default=1.0, gt=0.0)
    rationale: Optional[str] = None
    signature_proof: Optional[str] = None


class TaskDelegationPayload(BaseModel):
    task_id: str
    workflow_id: str
    parent_task_id: Optional[str] = None
    task_name: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Optional[Dict[str, Any]] = None
    required_skills: List[str] = Field(default_factory=list)
    rollback_instructions: Optional[Dict[str, Any]] = None
