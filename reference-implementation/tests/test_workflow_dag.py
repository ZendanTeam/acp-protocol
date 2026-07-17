"""Tests for Workflow DAG Execution, Voting Gates, and Saga Rollback."""
import pytest
from acp.models.manifest import AgentManifest, Skill, Endpoint
from acp.models.workflow import WorkflowDAG, WorkflowNode, RetryPolicy, RollbackAction, VotingRules
from acp.services.registry import RegistryService
from acp.services.discovery import DiscoveryService
from acp.services.memory import MemoryService
from acp.services.identity import IdentityProvider
from acp.services.security import SecurityEngine
from acp.transport.event_bus import EventBus
from acp.runtime.gateway import Gateway
from acp.runtime.router import Router
from acp.runtime.host import Host
from acp.orchestration.scheduler import Scheduler


@pytest.fixture
def test_mesh():
    idp = IdentityProvider()
    sec_engine = SecurityEngine(idp)
    reg = RegistryService()
    disc = DiscoveryService(reg)
    mem = MemoryService()
    event_bus = EventBus()
    
    gw = Gateway("gw_test", sec_engine)
    router = Router("rt_test", disc, event_bus)
    host = Host("host_test", gw, router, mem)
    scheduler = Scheduler("sched_test", router, mem)
    
    # Worker Agent
    m_worker = AgentManifest(
        did="did:acp:org:worker",
        name="Worker Agent",
        skills=[Skill(skill_id="compute", name="Compute", cost_credits_per_invocation=1.0)],
        endpoints=[Endpoint(transport="HTTP2", url="https://worker.local")]
    )
    reg.register_agent(m_worker)
    rt_worker = host.spawn_agent(m_worker)
    rt_worker.register_skill_handler("compute", lambda p, m, s: {"val": p.get("input", 0) * 2})
    rt_worker.register_skill_handler("rollback_compute", lambda p, m, s: {"status": "REVERTED"})
    
    # Auditor Agent
    m_auditor = AgentManifest(
        did="did:acp:org:auditor",
        name="Auditor Agent",
        skills=[Skill(skill_id="vote", name="Vote", cost_credits_per_invocation=0.5)],
        endpoints=[Endpoint(transport="WEBSOCKET", url="wss://auditor.local")]
    )
    reg.register_agent(m_auditor)
    rt_auditor = host.spawn_agent(m_auditor)
    rt_auditor.register_skill_handler("vote", lambda p, m, s: {"decision": "APPROVE"})
    
    return scheduler


def test_dag_execution_with_voting_gate(test_mesh):
    scheduler = test_mesh
    dag = WorkflowDAG(
        workflow_id="wf_test_1",
        name="Test Workflow",
        nodes=[
            WorkflowNode(
                node_id="n1",
                task_name="compute",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:worker",
                input_mapping={"input": 21}
            ),
            WorkflowNode(
                node_id="n2_gate",
                task_name="vote",
                execution_type="VOTING_GATE",
                dependencies=["n1"],
                voting_rules=VotingRules(required_voters=["did:acp:org:auditor"], consensus_threshold_pct=50.0)
            )
        ]
    )
    res = scheduler.execute_dag(dag)
    assert res["status"] == "SUCCESS"
    assert res["node_results"]["n1"]["val"] == 42
    assert res["node_results"]["n2_gate"]["status"] == "CONSENSUS_REACHED"


def test_saga_rollback_on_failure(test_mesh):
    scheduler = test_mesh
    dag = WorkflowDAG(
        workflow_id="wf_test_rollback",
        name="Rollback Workflow",
        nodes=[
            WorkflowNode(
                node_id="n1",
                task_name="compute",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:worker",
                input_mapping={"input": 10},
                rollback_action=RollbackAction(skill_id="rollback_compute", parameters={})
            ),
            WorkflowNode(
                node_id="n2_fail",
                task_name="non_existent_skill",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:worker",
                dependencies=["n1"],
                retry_policy=RetryPolicy(max_retries=1, backoff_ms=100)
            )
        ]
    )
    res = scheduler.execute_dag(dag)
    assert res["status"] == "FAILED_SAGA_ROLLBACK"
    assert len(res["rollback_trace"]) == 1
    assert res["rollback_trace"][0]["rollback_skill"] == "rollback_compute"
    assert res["rollback_trace"][0]["status"] == "SUCCESS"
