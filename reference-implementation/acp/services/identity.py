"""ACP Identity Provider (IdP) Implementation."""
import uuid
import time
from typing import Dict, List, Optional, Any
from acp.models.capability import CapabilityToken, CapabilityClaim


class IdentityProvider:
    """Root of Trust for minting DIDs, managing keys, and issuing Zero-Trust Capability Tokens."""

    def __init__(self, root_secret: str = "acp_idp_master_secret_key_2026") -> None:
        self.root_secret = root_secret
        self._did_keys: Dict[str, str] = {}  # DID -> Secret Key (or PubKey representation)

    def register_did(self, did: str, secret_key: Optional[str] = None) -> str:
        """Register a DID and its cryptographic signing key."""
        if not secret_key:
            secret_key = f"sk_{uuid.uuid4().hex}"
        self._did_keys[did] = secret_key
        return secret_key

    def get_secret_key(self, did: str) -> Optional[str]:
        return self._did_keys.get(did)

    def issue_capability_token(
        self,
        issuer_did: str,
        subject_did: str,
        capabilities: List[CapabilityClaim],
        ttl_seconds: int = 3600
    ) -> CapabilityToken:
        """Mint and sign a new CapabilityToken."""
        token = CapabilityToken(
            token_id=f"cap_{uuid.uuid4().hex[:12]}",
            issuer_did=issuer_did,
            subject_did=subject_did,
            issued_at_ns=int(time.time_ns()),
            expires_at_ns=int(time.time_ns()) + (ttl_seconds * 1_000_000_000),
            capabilities=capabilities
        )
        issuer_key = self.get_secret_key(issuer_did) or self.root_secret
        token.sign(issuer_key)
        return token

    def verify_capability_token(self, token: CapabilityToken) -> bool:
        """Verify cryptographic signature and expiration of a CapabilityToken."""
        issuer_key = self.get_secret_key(token.issuer_did) or self.root_secret
        if not token.verify_signature(issuer_key):
            return False
        if time.time_ns() > token.expires_at_ns:
            return False
        return True
