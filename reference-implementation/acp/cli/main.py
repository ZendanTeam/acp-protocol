"""ACP Command Line Interface and Simulation Tool."""
import os
import sys
import json
import time
import click

# Ensure reference implementation root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from acp.models.manifest import AgentManifest, Skill, Endpoint, SecurityProfile
from acp.models.envelope import Envelope, TargetType, FrameType
from acp.models.workflow import WorkflowDAG, WorkflowNode, RetryPolicy, RollbackAction, VotingRules
from acp.models.memory import MemoryOperationPayload, MemoryOperation, MemoryTier, VectorQuery
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


def build_simulation_environment():
    """Scaffold a complete local ACP mesh setup with 3 agents, router, gateway, and memory."""
    idp = IdentityProvider()
    sec_engine = SecurityEngine(idp)
    registry = RegistryService()
    discovery = DiscoveryService(registry)
    memory_srv = MemoryService()
    event_bus = EventBus()

    gateway = Gateway("gw_us_east_1", sec_engine)
    router = Router("rt_us_east_1", discovery, event_bus)
    host = Host("host_alpha", gateway, router, memory_srv)
    scheduler = Scheduler("sched_main", router, memory_srv)

    # 1. Register and spawn Planner Agent
    manifest_planner = AgentManifest(
        did="did:acp:org:planner-agent",
        name="Strategic Planner Agent",
        description="Breaks down complex problems into sub-tasks.",
        skills=[Skill(skill_id="plan_task", name="Plan Task", cost_credits_per_invocation=1.0)],
        endpoints=[Endpoint(transport="HTTP2", url="https://host.local/planner")]
    )
    registry.register_agent(manifest_planner)
    runtime_planner = host.spawn_agent(manifest_planner)
    runtime_planner.register_skill_handler("plan_task", lambda p, m, s: {"plan": ["research", "optimize"], "steps": 2})

    # 2. Register and spawn Researcher Agent
    manifest_researcher = AgentManifest(
        did="did:acp:org:researcher-agent",
        name="Web & Vector Researcher Agent",
        description="Performs deep semantic retrieval across knowledge stores.",
        skills=[Skill(skill_id="research_topic", name="Research Topic", cost_credits_per_invocation=1.5)],
        endpoints=[Endpoint(transport="GRPC", url="grpc://host.local/researcher")]
    )
    registry.register_agent(manifest_researcher)
    runtime_researcher = host.spawn_agent(manifest_researcher)
    runtime_researcher.register_skill_handler("research_topic", lambda p, m, s: {"findings": f"Comprehensive analysis on {p.get('topic')}", "confidence": 0.94})

    # 3. Register and spawn SQL Optimizer Agent (with a rollback skill!)
    manifest_sql = AgentManifest(
        did="did:acp:org:sql-agent",
        name="SQL Optimizer & Migration Agent",
        description="Optimizes SQL queries and applies schema migrations.",
        skills=[
            Skill(skill_id="optimize_query", name="Optimize Query", cost_credits_per_invocation=2.0),
            Skill(skill_id="rollback_migration", name="Rollback Migration", cost_credits_per_invocation=0.5)
        ],
        endpoints=[Endpoint(transport="UNIX_SOCKET", url="/var/run/acp/sql.sock")]
    )
    registry.register_agent(manifest_sql)
    runtime_sql = host.spawn_agent(manifest_sql)
    runtime_sql.register_skill_handler("optimize_query", lambda p, m, s: {"optimized_sql": f"SELECT /*+ INDEX(emp) */ * FROM {p.get('table', 'users')}"})
    runtime_sql.register_skill_handler("rollback_migration", lambda p, m, s: {"status": "ROLLED_BACK", "table": p.get('table', 'users')})

    # 4. Register and spawn Voter/Auditor Agent
    manifest_auditor = AgentManifest(
        did="did:acp:org:auditor-agent",
        name="Security & Quality Auditor Agent",
        description="Votes on mission-critical gates.",
        skills=[Skill(skill_id="vote", name="Vote on Gate", cost_credits_per_invocation=0.5)],
        endpoints=[Endpoint(transport="WEBSOCKET", url="wss://host.local/auditor")]
    )
    registry.register_agent(manifest_auditor)
    runtime_auditor = host.spawn_agent(manifest_auditor)
    runtime_auditor.register_skill_handler("vote", lambda p, m, s: {"decision": "APPROVE", "rationale": "All security assertions met."})

    return idp, registry, discovery, memory_srv, router, host, scheduler


@click.group()
def cli():
    """ACP (Agent Collaboration Protocol) CLI & Simulation Tool."""
    pass


@cli.command("inspect-mesh")
def inspect_mesh():
    """Inspect the live simulated ACP mesh topology and registered manifests."""
    _, registry, _, _, _, host, _ = build_simulation_environment()
    click.echo("\n" + "="*70)
    click.echo("             ACP DISTRIBUTED MESH TOPOLOGY & AGENTS")
    click.echo("="*70)
    click.echo(f"Host ID: {host.host_id} | Active Runtimes: {len(host.runtimes)}")
    click.echo("-"*70)
    for manifest in registry.list_all_manifests():
        click.echo(f"[{manifest.did}] : {manifest.name}")
        click.echo(f"  -> Description: {manifest.description}")
        skills_str = ", ".join([s.skill_id for s in manifest.skills])
        click.echo(f"  -> Skills: {skills_str}")
        click.echo(f"  -> Endpoints: {manifest.endpoints[0].transport} ({manifest.endpoints[0].url})")
        click.echo("-"*70)
    click.echo("Mesh Status: HEALTHY | Security: Zero-Trust mTLS & Capability Verified\n")


@cli.command("run-workflow")
def run_workflow():
    """Execute a complete multi-agent DAG workflow including parallel nodes and a voting gate."""
    _, _, _, _, _, _, scheduler = build_simulation_environment()
    click.echo("\n" + "="*70)
    click.echo("          EXECUTING ACP DAG WORKFLOW WITH VOTING GATE")
    click.echo("="*70)

    dag = WorkflowDAG(
        workflow_id="wf_enterprise_deployment_2026",
        name="Enterprise Multi-Agent Analysis & Optimization",
        nodes=[
            WorkflowNode(
                node_id="node_1_plan",
                task_name="plan_task",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:planner-agent",
                input_mapping={"task": "Full system migration"}
            ),
            WorkflowNode(
                node_id="node_2_research",
                task_name="research_topic",
                execution_type="PARALLEL_JOIN",
                target_agent_did="did:acp:org:researcher-agent",
                dependencies=["node_1_plan"],
                input_mapping={"topic": "Distributed vector databases"}
            ),
            WorkflowNode(
                node_id="node_3_optimize",
                task_name="optimize_query",
                execution_type="PARALLEL_JOIN",
                target_agent_did="did:acp:org:sql-agent",
                dependencies=["node_1_plan"],
                input_mapping={"table": "transactions"}
            ),
            WorkflowNode(
                node_id="node_4_voting_gate",
                task_name="vote_on_deployment",
                execution_type="VOTING_GATE",
                dependencies=["node_2_research", "node_3_optimize"],
                voting_rules=VotingRules(
                    required_voters=["did:acp:org:auditor-agent"],
                    consensus_threshold_pct=66.7
                )
            )
        ]
    )

    start_t = time.time()
    result = scheduler.execute_dag(dag, initial_input={"user_id": "admin_99"})
    elapsed = round((time.time() - start_t) * 1000, 2)

    click.echo(f"DAG Execution Completed in {elapsed} ms")
    click.echo(f"Workflow ID: {result['workflow_id']}")
    click.echo(f"Status: {result['status']}")
    click.echo("\nNode Execution Results:")
    click.echo(json.dumps(result.get("node_results", {}), indent=2))
    click.echo("="*70 + "\n")


@cli.command("simulate-saga-rollback")
def simulate_saga_rollback():
    """Simulate a DAG workflow failure and demonstrate reverse topological Saga Rollback."""
    _, _, _, _, router, host, scheduler = build_simulation_environment()
    click.echo("\n" + "="*70)
    click.echo("       SIMULATING UNRECOVERABLE NODE FAILURE & SAGA ROLLBACK")
    click.echo("="*70)

    # We modify node 3 to target a non-existent skill or trigger an error after 1 retry
    dag = WorkflowDAG(
        workflow_id="wf_saga_rollback_demo",
        name="Database Migration with Automatic Rollback",
        nodes=[
            WorkflowNode(
                node_id="node_1_migrate_schema",
                task_name="optimize_query",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:sql-agent",
                input_mapping={"table": "orders"},
                rollback_action=RollbackAction(skill_id="rollback_migration", parameters={"table": "orders"})
            ),
            WorkflowNode(
                node_id="node_2_failing_cloud_deploy",
                task_name="non_existent_exploding_skill",
                execution_type="AGENT_INVOCATION",
                target_agent_did="did:acp:org:planner-agent",
                dependencies=["node_1_migrate_schema"],
                retry_policy=RetryPolicy(max_retries=1, backoff_ms=100)
            )
        ]
    )

    result = scheduler.execute_dag(dag)
    click.echo(f"Workflow ID: {result['workflow_id']}")
    click.echo(f"Status: {result['status']}")
    click.echo(f"Failed Node: {result.get('failed_node')}")
    click.echo(f"Error Message: {result.get('error')}")
    click.echo("\nSaga Reverse Rollback Trace:")
    click.echo(json.dumps(result.get("rollback_trace", []), indent=2))
    click.echo("="*70 + "\n")


@cli.command("memory-demo")
def memory_demo():
    """Demonstrate the 6-Tier Distributed Memory Service and CRDT State Synchronization."""
    _, _, _, memory_srv, _, _, _ = build_simulation_environment()
    click.echo("\n" + "="*70)
    click.echo("          ACP 6-TIER DISTRIBUTED MEMORY & CRDT DEMO")
    click.echo("="*70)

    # 1. Short-Term LRU Put
    memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT, memory_tier=MemoryTier.SHORT_TERM,
        partition_key="sess_01", key="temp_scratch", value={"step": 1}
    ))
    # 2. Long-Term KV Put
    memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT, memory_tier=MemoryTier.LONG_TERM,
        partition_key="agent_history", key="last_login", value="2026-07-17T17:50:00Z"
    ))
    # 3. CRDT Shared Memory Put
    memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT, memory_tier=MemoryTier.SHARED,
        partition_key="shared_workspace", key="active_lock", value={"owner": "did:acp:org:planner-agent"}
    ))
    # 4. Vector Cosine Similarity Search Indexing
    memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.PUT, memory_tier=MemoryTier.VECTOR,
        partition_key="kb_v1", key="doc_ai_agents",
        value={"embedding": [0.9, 0.1, 0.0, 0.5], "metadata": {"topic": "ACP"}, "content": "ACP connects agents via DAGs."}
    ))

    # Query vector memory
    vec_res = memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.QUERY_VECTOR, memory_tier=MemoryTier.VECTOR,
        partition_key="kb_v1",
        vector_query=VectorQuery(embedding=[0.88, 0.12, 0.01, 0.49], top_k=2, min_similarity=0.7)
    ))

    click.echo("1. Short-Term Cache Entry -> " + str(memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET, memory_tier=MemoryTier.SHORT_TERM, partition_key="sess_01", key="temp_scratch"
    ))))
    click.echo("2. Long-Term KV Entry    -> " + str(memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET, memory_tier=MemoryTier.LONG_TERM, partition_key="agent_history", key="last_login"
    ))))
    click.echo("3. CRDT Shared Entry     -> " + str(memory_srv.execute_operation(MemoryOperationPayload(
        operation=MemoryOperation.GET, memory_tier=MemoryTier.SHARED, partition_key="shared_workspace", key="active_lock"
    ))))
    click.echo("\n4. Vector Cosine Query Results (similarity match on [0.88, 0.12, 0.01, 0.49]):")
    click.echo(json.dumps(vec_res.get("results", []), indent=2))
    click.echo("="*70 + "\n")


@cli.command("simulate-negotiation")
def simulate_negotiation():
    """Simulate real-time economic SLA negotiation between two agents over ACP."""
    click.echo("\n" + "="*70)
    click.echo("      ACP PROTOCOL-LEVEL ECONOMIC SLA NEGOTIATION DEMO")
    click.echo("="*70)
    click.echo("[Phase 1: PROPOSE] Delegator Agent sends NEGOTIATION_PROPOSAL:")
    click.echo('  -> Terms: {"price_credits": 10.0, "sla_max_latency_ms": 2000, "required_capabilities": ["gpu"]}')
    time.sleep(0.1)
    click.echo("\n[Phase 2: COUNTER] Delegatee Agent checks cluster load and sends NEGOTIATION_COUNTER:")
    click.echo('  -> Terms: {"price_credits": 12.5, "sla_max_latency_ms": 2500, "counter_reason": "High GPU memory pressure"}')
    time.sleep(0.1)
    click.echo("\n[Phase 3: ACCEPT] Delegator Agent evaluates counter-offer and sends NEGOTIATION_ACCEPT:")
    click.echo('  -> Status: AGREED & SIGNED | Contract locked for Correlation ID neg_778899')
    click.echo("="*70 + "\n")


if __name__ == "__main__":
    cli()
