# ACP Workflow Engine & Orchestration Specification
**Document Number:** RFC-ACP-004  
**Version:** 1.0.0  

---

## 1. Directed Acyclic Graph (DAG) Workflow Architecture

The **ACP Workflow Engine** (`ACP Scheduler`) provides distributed orchestration, planning, and execution for complex multi-agent tasks. Unlike single-agent loops that can enter infinite hallucination spirals or stall on failures, ACP formalizes workflows as rigorous **Directed Acyclic Graphs (`workflow-dag.schema.json`)**.

```
+-----------------------------------------------------------------------------------------------+
|                                   SAMPLE ACP WORKFLOW DAG                                     |
|                                                                                               |
|                                     +--------------------+                                    |
|                                     |  Node 1: PLANNER   |                                    |
|                                     |  (Task Breakdown)  |                                    |
|                                     +--------------------+                                    |
|                                                |                                              |
|                           +--------------------+--------------------+                         |
|                           |                                         |                         |
|                           v                                         v                         |
|                +--------------------+                    +--------------------+               |
|                | Node 2A: RESEARCH  |                    | Node 2B: CODE GEN  |               |
|                | (Skill: web_search)|                    | (Skill: python_dev)|               |
|                +--------------------+                    +--------------------+               |
|                           |                                         |                         |
|                           +--------------------+--------------------+                         |
|                                                |                                              |
|                                                v                                              |
|                                     +--------------------+                                    |
|                                     | Node 3: PARALLEL   |                                    |
|                                     |        JOIN        |                                    |
|                                     +--------------------+                                    |
|                                                |                                              |
|                                                v                                              |
|                                     +--------------------+                                    |
|                                     | Node 4: VOTING GATE|                                    |
|                                     | (Consensus >= 66%) |                                    |
|                                     +--------------------+                                    |
|                                           |         |                                         |
|                                           | [PASS]  | [FAIL: Rollback]                        |
|                                           v         v                                         |
|                              +------------------+  +------------------+                       |
|                              | Node 5: DEPLOY   |  | Node 6: ROLLBACK |                       |
|                              | (Cloud Execution)|  | (Revert Changes) |                       |
|                              +------------------+  +------------------+                       |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Core Workflow Capabilities

### 2.1 Task Delegation (`TASK_DELEGATION`)
An agent (the *Delegator*) can offload a sub-problem to another agent or compute cluster (the *Delegatee*) via the `TASK_DELEGATION` frame payload.
- The Delegator specifies `task_id`, `parent_task_id`, `required_skills`, `input_data`, and a strict `timeout_ms`.
- The Delegatee responds with periodic `TASK_STATUS` event frames (`status: IN_PROGRESS`, `progress_pct: 50%`) and a final `RESPONSE` when complete.
- If the Delegatee becomes unresponsive (misses two consecutive `TASK_STATUS` updates or heartbeats), the ACP Scheduler automatically reassigns the task to another capable agent from the Discovery pool.

### 2.2 Dynamic Planning
Workflows need not be static. An autonomous planning agent (`execution_type: AGENT_INVOCATION`) can dynamically construct and emit a new sub-DAG payload at runtime (`SUB_WORKFLOW`). The Scheduler ingests this sub-DAG, validates node dependencies, and weaves it into the active execution graph.

### 2.3 Negotiation & SLA Contracts
Before executing computationally intensive or expensive tasks, agents engage in **Protocol-Level Negotiation**:
1. **Proposal (`NEGOTIATION_PROPOSAL`):** Delegator sends terms: `{"price_credits": 15.0, "sla_max_latency_ms": 5000, "required_capabilities": ["gpu_v100"]}`.
2. **Counter (`NEGOTIATION_COUNTER`):** Delegatee checks current cluster load and counters: `{"price_credits": 18.0, "sla_max_latency_ms": 6000, "counter_reason": "High GPU contention"}`.
3. **Accept/Reject (`NEGOTIATION_ACCEPT` / `NEGOTIATION_REJECT`):** Delegator accepts the terms, locking in a cryptographically signed **SLA Contract** for the duration of the task.

### 2.4 Multi-Agent Voting & Consensus Gates (`VOTING_GATE`)
To eliminate hallucinations, enforce safety policies, or achieve high-precision consensus on mission-critical actions (e.g., executing financial trades or deploying infrastructure), workflows incorporate explicit `VOTING_GATE` nodes:
- The Scheduler broadcasts a `VOTE_CAST` request to a designated panel of evaluator agents (`voting_rules.required_voters`).
- Each voter independently evaluates the upstream results and replies with its decision (`APPROVE`, `REJECT`, or `ABSTAIN`), optional `weight`, and a cryptographic `signature_proof`.
- If the weighted sum of `APPROVE` votes meets or exceeds `consensus_threshold_pct` (default `66.7%`), the DAG proceeds to downstream nodes. Otherwise, the node is marked as `FAILED`, triggering conflict resolution or rollback.

### 2.5 Conflict Resolution
When a voting gate fails or multiple parallel agents produce diverging outputs for the same task, the Scheduler invokes a configured **Conflict Resolution Policy**:
- **Majority Vote:** Select the output agreed upon by `>50%` of workers.
- **Judge Arbitration:** Delegate the conflicting outputs to a specialized higher-tier LLM/Arbiter agent (`did:acp:arbiter`) with instructions to synthesize the correct resolution.
- **Human Escalation:** Emit an `Agent -> Human` request asking an operator to manually select the valid outcome (`HITL`).

### 2.6 Automatic Retries with Exponential Backoff
When a node execution fails due to network timeouts (`408`), transient agent crashes (`503`), or rate limits (`429`), the Scheduler executes the node's `retry_policy`:
```
WaitTime(attempt) = Min( max_backoff_ms, backoff_ms * (multiplier ^ (attempt - 1)) + Jitter() )
```
If all attempts (`max_retries`, default 3) are exhausted without success, the node transitions to `FAILED_EXHAUSTED`.

### 2.7 Compensating Transactions & Rollback (`rollback_action`)
In distributed AI workflows, standard database ACID transactions do not apply across heterogeneous APIs and clouds. ACP implements the **Saga Architectural Pattern** for rollback:
- Every node in a DAG can declare a `rollback_action` (e.g., Node: *Create Cloud Bucket* -> Rollback: *Delete Cloud Bucket*).
- If any downstream node fails irrecoverably, the Scheduler traverses the graph in **Reverse Topological Order**, executing the `rollback_action` of every previously completed node to restore the system to a clean baseline state.

### 2.8 Parallel Execution & Dependency Graphs (`PARALLEL_JOIN`)
The Scheduler continuously computes the **in-degree** (number of unsatisfied upstream dependencies) for every node:
- When Node $X$'s dependencies all reach `COMPLETED`, its in-degree becomes $0$, and the Scheduler dispatches Node $X$ immediately.
- Nodes sharing no mutual dependencies are dispatched concurrently to independent agents across the network (`PARALLEL_JOIN`).

### 2.9 Event Subscriptions (`acp.events.*`)
Agents and external dashboards can subscribe to real-time workflow lifecycle events via the ACP Broker using wildcard topic subscriptions:
- `acp.events.workflow.started`: Emitted when a DAG execution begins.
- `acp.events.workflow.node.completed`: Emitted after each individual node completes successfully.
- `acp.events.workflow.negotiation.agreed`: Emitted when two agents agree on task terms.
- `acp.events.workflow.failed`: Emitted upon unrecoverable DAG failure.

### 2.10 Checkpoints & Resumable Workflows
Long-running AI workflows (e.g., processing a 10,000-file repository or running multi-day research sweeps) must survive host reboots, network partitions, and process migrations.
- **Automatic Checkpointing:** After each completed node (if `checkpoint_strategy: AFTER_EACH_NODE`), the Scheduler writes a complete **State Snapshot** to the ACP Memory Service (`operation: CREATE_SNAPSHOT`), capturing node status, intermediate outputs, and execution context.
- **Resumability:** If an ACP Host or Scheduler crashes mid-workflow, a standby Scheduler detects the lease expiration, retrieves the latest checkpoint from memory (`operation: RESTORE_SNAPSHOT`), and resumes execution exactly from the first uncompleted node without re-running expensive upstream tasks.
