"""Zero-Trust Capability Token Models."""
import json
import time
import hmac
import hashlib
import base64
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CapabilityClaim(BaseModel):
    resource: str  # URI pattern, e.g., 'memory://short-term/session-1/*' or 'agent://did:acp:worker/execute'
    actions: List[str]  # ['READ', 'WRITE', 'EXECUTE', 'DELETE', 'DELEGATE', 'SUBSCRIBE']
    conditions: Optional[Dict[str, Any]] = None


class CapabilityToken(BaseModel):
    token_id: str
    issuer_did: str = Field(..., pattern=r"^did:acp:[a-zA-Z0-9_:-]+$")
    subject_did: str = Field(..., pattern=r"^did:acp:[a-zA-Z0-9_:-]+$")
    issued_at_ns: int = Field(default_factory=lambda: int(time.time_ns()))
    expires_at_ns: int = Field(default_factory=lambda: int(time.time_ns()) + 3_600_000_000_000)  # +1 hr default
    capabilities: List[CapabilityClaim] = Field(default_factory=list)
    signature: Optional[str] = None

    def to_canonical_json(self) -> str:
        data = {
            "token_id": self.token_id,
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "issued_at_ns": self.issued_at_ns,
            "expires_at_ns": self.expires_at_ns,
            "capabilities": [c.model_dump(exclude_none=True) for c in self.capabilities]
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def sign(self, issuer_secret_key: str) -> str:
        canonical = self.to_canonical_json().encode("utf-8")
        sig_bytes = hmac.new(issuer_secret_key.encode("utf-8"), canonical, hashlib.sha256).digest()
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        self.signature = sig_b64
        return sig_b64

    def verify_signature(self, issuer_secret_key: str) -> bool:
        if not self.signature:
            return False
        canonical = self.to_canonical_json().encode("utf-8")
        expected_bytes = hmac.new(issuer_secret_key.encode("utf-8"), canonical, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(expected_bytes).decode("utf-8")
        return hmac.compare_digest(self.signature, expected_b64)

    def is_valid_for(self, action: str, resource_uri: str, current_time_ns: Optional[int] = None) -> bool:
        """Verify token expiration and check if requested action is permitted for the given resource URI."""
        if current_time_ns is None:
            current_time_ns = time.time_ns()
        if current_time_ns > self.expires_at_ns:
            return False

        for cap in self.capabilities:
            if action in cap.actions:
                # Simple wildcard matching or prefix check
                pattern = cap.resource
                if pattern.endswith("/*"):
                    prefix = pattern[:-2]
                    if resource_uri.startswith(prefix):
                        return True
                elif pattern == resource_uri:
                    return True
        return False
