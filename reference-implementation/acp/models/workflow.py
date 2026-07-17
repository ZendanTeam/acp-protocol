"""Workflow and DAG Pydantic Models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    max_retries: int = Field(default=3, ge=0)
    backoff_ms: int = Field(default=1000, ge=100)
    multiplier: float = Field(default=2.0, ge=1.0)


class RollbackAction(BaseModel):
    skill_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class VotingRules(BaseModel):
    required_voters: List[str] = Field(default_factory=list)
    consensus_threshold_pct: float = Field(default=66.7, ge=0.0, le=100.0)
    timeout_ms: int = Field(default=60000)


class WorkflowNode(BaseModel):
    node_id: str
    task_name: str
    execution_type: str  # AGENT_INVOCATION, PARALLEL_JOIN, VOTING_GATE, NEGOTIATION_GATE, HUMAN_APPROVAL, SUB_WORKFLOW
    target_agent_did: Optional[str] = None
    target_skill_query: Optional[Dict[str, Any]] = None
    input_mapping: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    rollback_action: Optional[RollbackAction] = None
    voting_rules: Optional[VotingRules] = None


class WorkflowDAG(BaseModel):
    workflow_id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    global_timeout_ms: int = Field(default=300000)
    checkpoint_strategy: str = "AFTER_EACH_NODE"
    nodes: List[WorkflowNode] = Field(default_factory=list)
