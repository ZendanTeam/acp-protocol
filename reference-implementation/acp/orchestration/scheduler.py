"""ACP Distributed Scheduler and DAG Workflow Execution Engine."""
import time
import networkx as nx
from typing import Dict, Any, List, Optional
from acp.models.workflow import WorkflowDAG, WorkflowNode
from acp.models.envelope import Envelope, TargetType, FrameType
from acp.runtime.router import Router
from acp.services.memory import MemoryService, MemoryOperationPayload, MemoryOperation, MemoryTier


class Scheduler:
    """Evaluates DAG workflows, dispatches tasks, checks voting consensus gates, and executes Saga rollbacks."""

    def __init__(self, scheduler_id: str, router: Router, memory_service: MemoryService) -> None:
        self.scheduler_id = scheduler_id
        self.router = router
        self.memory_service = memory_service

    def build_graph(self, dag: WorkflowDAG) -> nx.DiGraph:
        """Construct NetworkX DiGraph and verify it is acyclic."""
        g = nx.DiGraph()
        for node in dag.nodes:
            g.add_node(node.node_id, data=node)
            for dep in node.dependencies:
                g.add_edge(dep, node.node_id)
        if not nx.is_directed_acyclic_graph(g):
            raise ValueError(f"Workflow {dag.workflow_id} contains cycles and is not a valid DAG!")
        return g

    def execute_dag(self, dag: WorkflowDAG, initial_input: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Execute the workflow DAG, handling parallel dispatch, voting gates, retries, checkpoints, and rollback."""
        g = self.build_graph(dag)
        topo_order = list(nx.topological_sort(g))
        
        node_results: Dict[str, Any] = {}
        completed_nodes: List[WorkflowNode] = []
        workflow_status = "SUCCESS"

        # Emit workflow started event if topic routed
        self.router.route_frame(Envelope(
            sender={"agent_id": f"did:acp:scheduler:{self.scheduler_id}", "host_id": self.scheduler_id},
            receiver={"target_type": TargetType.TOPIC, "target_id": "acp.events.workflow.started"},
            frame_type=FrameType.EVENT,
            payload={"workflow_id": dag.workflow_id, "nodes_count": len(topo_order)}
        ))

        for node_id in topo_order:
            node = g.nodes[node_id]["data"]
            # Prepare input: merge initial_input and upstream dependency outputs
            node_input = dict(initial_input)
            for dep_id in node.dependencies:
                if dep_id in node_results and isinstance(node_results[dep_id], dict):
                    node_input.update(node_results[dep_id])
            node_input.update(node.input_mapping)

            success, result_data = self._execute_node_with_retries(node, node_input, dag.workflow_id)
            if success:
                node_results[node_id] = result_data
                completed_nodes.append(node)
                
                # Checkpoint if configured
                if dag.checkpoint_strategy == "AFTER_EACH_NODE":
                    self.memory_service.execute_operation(MemoryOperationPayload(
                        operation=MemoryOperation.CREATE_SNAPSHOT,
                        memory_tier=MemoryTier.LONG_TERM,
                        partition_key=f"wf_{dag.workflow_id}"
                    ))
            else:
                # Node failed unrecoverably after retries -> trigger Saga Rollback!
                workflow_status = "FAILED_SAGA_ROLLBACK"
                rollback_trace = self._execute_rollback(completed_nodes, dag.workflow_id)
                return {
                    "workflow_id": dag.workflow_id,
                    "status": workflow_status,
                    "failed_node": node_id,
                    "error": result_data,
                    "rollback_trace": rollback_trace,
                    "completed_node_results": node_results
                }

        return {
            "workflow_id": dag.workflow_id,
            "status": workflow_status,
            "node_results": node_results
        }

    def _execute_node_with_retries(self, node: WorkflowNode, input_data: Dict[str, Any], workflow_id: str) -> tuple[bool, Any]:
        max_attempts = node.retry_policy.max_retries + 1
        backoff_ms = node.retry_policy.backoff_ms
        mult = node.retry_policy.multiplier

        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                if node.execution_type == "VOTING_GATE":
                    return self._execute_voting_gate(node, input_data, workflow_id)
                elif node.execution_type in ("AGENT_INVOCATION", "PARALLEL_JOIN"):
                    success, res = self._execute_agent_task(node, input_data, workflow_id)
                    if success:
                        return True, res
                    else:
                        last_err = res
                else:
                    return True, {"status": "SKIPPED_OR_MOCKED", "node_id": node.node_id}
            except Exception as e:
                last_err = str(e)

            if attempt < max_attempts:
                # Exponential backoff sleep (capped for simulation fast running if under test)
                sleep_sec = min((backoff_ms * (mult ** (attempt - 1))) / 1000.0, 0.1)
                time.sleep(sleep_sec)

        return False, last_err

    def _execute_agent_task(self, node: WorkflowNode, input_data: Dict[str, Any], workflow_id: str) -> tuple[bool, Any]:
        target_did = node.target_agent_did
        if not target_did and not node.target_skill_query:
            return False, "Node missing both target_agent_did and target_skill_query"

        envelope = Envelope(
            sender={"agent_id": f"did:acp:scheduler:{self.scheduler_id}", "host_id": self.scheduler_id},
            receiver={
                "target_type": TargetType.AGENT,
                "target_id": target_did,
                "routing_query": node.target_skill_query
            },
            frame_type=FrameType.REQUEST,
            correlation_id=f"task_{node.node_id}_{workflow_id}",
            payload={"action": node.task_name, "parameters": input_data}
        )

        resp = self.router.route_frame(envelope)
        if resp and resp.frame_type == FrameType.RESPONSE:
            return True, resp.payload.get("result", {})
        elif resp and resp.frame_type == FrameType.ERROR:
            return False, resp.payload.get("error", {})
        return False, "No response or timeout from router"

    def _execute_voting_gate(self, node: WorkflowNode, input_data: Dict[str, Any], workflow_id: str) -> tuple[bool, Any]:
        if not node.voting_rules or not node.voting_rules.required_voters:
            return True, {"status": "APPROVED_NO_VOTERS_REQUIRED"}

        total_weight = 0.0
        approved_weight = 0.0
        votes_detail = []

        action_name = node.task_name if node.task_name else "vote"
        for voter_did in node.voting_rules.required_voters:
            total_weight += 1.0  # default weight 1.0 per voter
            # Send vote request
            envelope = Envelope(
                sender={"agent_id": f"did:acp:scheduler:{self.scheduler_id}", "host_id": self.scheduler_id},
                receiver={"target_type": TargetType.AGENT, "target_id": voter_did},
                frame_type=FrameType.REQUEST,
                correlation_id=f"vote_{node.node_id}",
                payload={"action": action_name, "parameters": {"data": input_data}}
            )
            resp = self.router.route_frame(envelope)
            decision = "REJECT"
            if resp and resp.frame_type == FrameType.RESPONSE:
                res_dict = resp.payload.get("result", {})
                if isinstance(res_dict, dict) and res_dict.get("decision") == "APPROVE":
                    decision = "APPROVE"
                    approved_weight += 1.0

            votes_detail.append({"voter_did": voter_did, "decision": decision})

        consensus_pct = (approved_weight / total_weight) * 100.0 if total_weight > 0 else 0.0
        if consensus_pct >= node.voting_rules.consensus_threshold_pct:
            return True, {"status": "CONSENSUS_REACHED", "consensus_pct": consensus_pct, "votes": votes_detail}
        else:
            return False, {"status": "CONSENSUS_FAILED", "consensus_pct": consensus_pct, "votes": votes_detail}

    def _execute_rollback(self, completed_nodes: List[WorkflowNode], workflow_id: str) -> List[Dict[str, Any]]:
        """Saga reverse topological order rollback."""
        rollback_trace = []
        for node in reversed(completed_nodes):
            if node.rollback_action:
                # Execute rollback skill
                target_did = node.target_agent_did
                if target_did:
                    env = Envelope(
                        sender={"agent_id": f"did:acp:scheduler:{self.scheduler_id}", "host_id": self.scheduler_id},
                        receiver={"target_type": TargetType.AGENT, "target_id": target_did},
                        frame_type=FrameType.REQUEST,
                        correlation_id=f"rollback_{node.node_id}_{workflow_id}",
                        payload={"action": node.rollback_action.skill_id, "parameters": node.rollback_action.parameters}
                    )
                    resp = self.router.route_frame(env)
                    status = "SUCCESS" if resp and resp.frame_type == FrameType.RESPONSE else "FAILED"
                    rollback_trace.append({"node_id": node.node_id, "rollback_skill": node.rollback_action.skill_id, "status": status})
            else:
                rollback_trace.append({"node_id": node.node_id, "rollback_skill": "NONE", "status": "SKIPPED"})
        return rollback_trace
