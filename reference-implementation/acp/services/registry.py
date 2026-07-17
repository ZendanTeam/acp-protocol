"""ACP Registry Service Implementation."""
from typing import Dict, Optional, List
from acp.models.manifest import AgentManifest


class RegistryService:
    """Authoritative, ACID-backed catalog of verified Agent Manifests."""

    def __init__(self) -> None:
        self._manifests: Dict[str, AgentManifest] = {}

    def register_agent(self, manifest: AgentManifest) -> None:
        """Register or update an agent's manifest."""
        self._manifests[manifest.did] = manifest

    def deregister_agent(self, did: str) -> bool:
        """Remove an agent manifest from the registry."""
        if did in self._manifests:
            del self._manifests[did]
            return True
        return False

    def get_manifest(self, did: str) -> Optional[AgentManifest]:
        """Retrieve the exact manifest by DID."""
        return self._manifests.get(did)

    def list_all_manifests(self) -> List[AgentManifest]:
        """List all currently registered manifests."""
        return list(self._manifests.values())

    def get_pubkey(self, did: str) -> Optional[str]:
        """Fetch the base64 public key associated with a DID."""
        manifest = self._manifests.get(did)
        if manifest and manifest.security_profile:
            return manifest.security_profile.pubkey_base64
        return None
