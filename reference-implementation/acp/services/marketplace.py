"""ACP Marketplace Service Implementation."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MarketplaceArtifact(BaseModel):
    artifact_id: str
    name: str
    version: str
    artifact_type: str  # SKILL, PLUGIN, TOOL, MODEL, WORKFLOW, TEMPLATE, KNOWLEDGE_PACK
    publisher_did: str
    description: str
    content_uri: str  # e.g., acp://registry.acp.protocol.org/skills/sql_opt:v1.0.0
    payload_schema: Optional[Dict[str, Any]] = None
    verified_status: str = "PENDING"  # PENDING, VERIFIED, REJECTED
    signature: Optional[str] = None


class MarketplaceService:
    """Decentralized Catalog for skills, plugins, workflows, and knowledge packs."""

    def __init__(self) -> None:
        self.artifacts: Dict[str, MarketplaceArtifact] = {}

    def publish_artifact(self, artifact: MarketplaceArtifact) -> str:
        """Publish an artifact to the marketplace. Runs simulation verification."""
        # Simulate verification check
        if artifact.publisher_did.startswith("did:acp:"):
            artifact.verified_status = "VERIFIED"
        else:
            artifact.verified_status = "REJECTED"
        self.artifacts[artifact.artifact_id] = artifact
        return artifact.verified_status

    def get_artifact(self, artifact_id: str) -> Optional[MarketplaceArtifact]:
        return self.artifacts.get(artifact_id)

    def search_artifacts(self, artifact_type: Optional[str] = None, keyword: Optional[str] = None) -> List[MarketplaceArtifact]:
        results = []
        for item in self.artifacts.values():
            if item.verified_status != "VERIFIED":
                continue
            if artifact_type and item.artifact_type.upper() != artifact_type.upper():
                continue
            if keyword and keyword.lower() not in item.name.lower() and keyword.lower() not in item.description.lower():
                continue
            results.append(item)
        return results
