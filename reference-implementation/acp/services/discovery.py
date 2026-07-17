"""ACP Discovery Service Implementation."""
from typing import Dict, Any, List, Optional
from acp.services.registry import RegistryService
from acp.models.manifest import AgentManifest


class DiscoveryService:
    """Real-time Discovery Engine supporting skill queries, SLA matching, and local peer search."""

    def __init__(self, registry: RegistryService) -> None:
        self.registry = registry
        # Live node status (heartbeats, load metrics)
        self.node_status: Dict[str, Dict[str, Any]] = {}

    def update_heartbeat(self, did: str, status_metrics: Dict[str, Any]) -> None:
        """Update live compute availability and SLA metrics for a registered agent."""
        self.node_status[did] = status_metrics

    def search_by_skill(self, required_skill_id: str, max_cost_credits: Optional[float] = None) -> List[AgentManifest]:
        """Find agents offering a specific skill ID within cost budget."""
        results = []
        for manifest in self.registry.list_all_manifests():
            for skill in manifest.skills:
                if skill.skill_id == required_skill_id:
                    if max_cost_credits is not None and skill.cost_credits_per_invocation > max_cost_credits:
                        continue
                    results.append(manifest)
                    break
        return results

    def search_by_query(self, query: Dict[str, Any]) -> List[AgentManifest]:
        """Dynamic routing query match (skills, models, SLA constraints)."""
        required_skills: List[str] = query.get("required_skills", [])
        required_model_provider: Optional[str] = query.get("model_provider")
        max_cost: Optional[float] = query.get("max_cost_credits")

        results = []
        for manifest in self.registry.list_all_manifests():
            # Check skills
            if required_skills:
                manifest_skill_ids = {s.skill_id for s in manifest.skills}
                if not set(required_skills).issubset(manifest_skill_ids):
                    continue

            # Check models
            if required_model_provider:
                if not any(m.provider == required_model_provider for m in manifest.models):
                    continue

            # Check cost
            if max_cost is not None:
                if any(s.cost_credits_per_invocation > max_cost for s in manifest.skills):
                    continue

            results.append(manifest)
        return results
