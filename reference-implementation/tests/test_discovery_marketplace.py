"""Tests for Discovery and Marketplace Services."""
import pytest
from acp.models.manifest import AgentManifest, Skill, Endpoint
from acp.services.registry import RegistryService
from acp.services.discovery import DiscoveryService
from acp.services.marketplace import MarketplaceService, MarketplaceArtifact


def test_discovery_by_skill_and_cost():
    reg = RegistryService()
    disc = DiscoveryService(reg)
    
    m1 = AgentManifest(
        did="did:acp:org:cheap-agent",
        name="Cheap Agent",
        skills=[Skill(skill_id="data_clean", name="Data Clean", cost_credits_per_invocation=1.0)],
        endpoints=[Endpoint(transport="HTTP2", url="https://a1.local")]
    )
    m2 = AgentManifest(
        did="did:acp:org:expensive-agent",
        name="Expensive Agent",
        skills=[Skill(skill_id="data_clean", name="Data Clean", cost_credits_per_invocation=10.0)],
        endpoints=[Endpoint(transport="GRPC", url="grpc://a2.local")]
    )
    reg.register_agent(m1)
    reg.register_agent(m2)
    
    # Search without cost limit
    res_all = disc.search_by_skill("data_clean")
    assert len(res_all) == 2
    
    # Search with budget 5.0
    res_budget = disc.search_by_skill("data_clean", max_cost_credits=5.0)
    assert len(res_budget) == 1
    assert res_budget[0].did == "did:acp:org:cheap-agent"


def test_marketplace_verification():
    mkt = MarketplaceService()
    art_valid = MarketplaceArtifact(
        artifact_id="art_001",
        name="SQL Optimizer Skill",
        version="1.0.0",
        artifact_type="SKILL",
        publisher_did="did:acp:org:verified-dev",
        description="Optimizes SQL queries via semantic indexing",
        content_uri="acp://registry.acp.protocol.org/skills/sql:v1.0.0"
    )
    
    status = mkt.publish_artifact(art_valid)
    assert status == "VERIFIED"
    
    search_res = mkt.search_artifacts(artifact_type="SKILL", keyword="semantic")
    assert len(search_res) == 1
    assert search_res[0].artifact_id == "art_001"
