"""Tests validating JSON payloads against formal ACP JSON Schemas."""
import json
import os
import pytest
import jsonschema

SCHEMA_DIR = "/home/user/acp/schemas"


def load_schema(filename: str) -> dict:
    with open(os.path.join(SCHEMA_DIR, filename)) as fp:
        return json.load(fp)


def test_envelope_schema_valid():
    schema = load_schema("envelope.schema.json")
    valid_envelope = {
        "acp_version": "1.0.0",
        "message_id": "01H2X3Y4Z5A6B7C8D9E0F1G2H3",
        "correlation_id": "corr_001",
        "timestamp_ns": 1784311200000000000,
        "ttl_ms": 30000,
        "sender": {
            "agent_id": "did:acp:org:sender-agent",
            "host_id": "host_us_east_1"
        },
        "receiver": {
            "target_type": "AGENT",
            "target_id": "did:acp:org:receiver-agent"
        },
        "frame_type": "REQUEST",
        "routing": {
            "hop_count": 0,
            "max_hops": 16,
            "router_path": []
        },
        "security": {
            "nonce": "abc123nonce",
            "signature": "c2lnbmF0dXJl"
        },
        "payload": {
            "action": "sql_query",
            "parameters": {"query": "SELECT * FROM users"}
        }
    }
    jsonschema.validate(instance=valid_envelope, schema=schema)


def test_envelope_schema_invalid():
    schema = load_schema("envelope.schema.json")
    # Missing required field 'sender'
    invalid_envelope = {
        "acp_version": "1.0.0",
        "message_id": "msg_001",
        "timestamp_ns": 1784311200000000000,
        "receiver": {"target_type": "AGENT"},
        "frame_type": "REQUEST",
        "payload": {}
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_envelope, schema=schema)


def test_agent_manifest_schema_valid():
    schema = load_schema("agent-manifest.schema.json")
    valid_manifest = {
        "did": "did:acp:finance:tax-optimizer",
        "name": "Tax Optimizer Agent",
        "version": "1.2.0",
        "description": "Calculates tax deductions.",
        "skills": [
            {
                "skill_id": "optimize_tax",
                "name": "Optimize Tax",
                "input_schema": {},
                "output_schema": {},
                "cost_credits_per_invocation": 3.5
            }
        ],
        "endpoints": [
            {
                "transport": "GRPC",
                "url": "grpc://tax.local:50051",
                "tls_required": True
            }
        ],
        "security_profile": {
            "supported_auth": ["CAPABILITY_TOKEN", "MTLS"],
            "sandboxed": True,
            "isolation_level": "CONTAINER"
        }
    }
    jsonschema.validate(instance=valid_manifest, schema=schema)


def test_workflow_dag_schema_valid():
    schema = load_schema("workflow-dag.schema.json")
    valid_dag = {
        "workflow_id": "wf_101",
        "name": "Test DAG",
        "version": "1.0.0",
        "nodes": [
            {
                "node_id": "node_1",
                "task_name": "task_a",
                "execution_type": "AGENT_INVOCATION",
                "target_agent_did": "did:acp:org:worker",
                "dependencies": []
            }
        ]
    }
    jsonschema.validate(instance=valid_dag, schema=schema)
