"""ACP Gateway Implementation for Perimeter Defense and Security Enforcement."""
from typing import Dict, Any, Optional
from acp.models.envelope import Envelope, FrameType
from acp.services.security import SecurityEngine


class Gateway:
    """Ingress/Egress Gateway enforcing mTLS verification, Replay checks, Rate Limits, and Secrets Injection."""

    def __init__(self, gateway_id: str, security_engine: SecurityEngine) -> None:
        self.gateway_id = gateway_id
        self.security_engine = security_engine

    def process_ingress(self, envelope: Envelope) -> Dict[str, Any]:
        """Validate ingress envelope before allowing it into the internal mesh/router."""
        # Check security via engine
        check_result = self.security_engine.verify_ingress_frame(envelope)
        if check_result["status"] != "ALLOWED":
            return check_result

        # Check frame expiration
        if envelope.is_expired():
            return {"status": "REJECTED", "code": 408, "reason": "Frame TTL expired"}

        return {"status": "ALLOWED", "code": 200, "envelope": envelope}

    def process_egress(self, envelope: Envelope) -> Envelope:
        """Inspect and transform egress payload (e.g., injecting secrets from the Secrets Vault)."""
        if envelope.payload:
            envelope.payload = self.security_engine.inject_secrets(envelope.payload)
        return envelope
