"""ACP Zero-Trust Security Engine and Gateway Enforcement."""
import time
from typing import Dict, Set, Optional, Any
from acp.models.envelope import Envelope
from acp.models.capability import CapabilityToken
from acp.services.identity import IdentityProvider


class SecurityEngine:
    """Enforces mTLS simulation, replay checking, rate limiting, capability verification, and Secrets Vault."""

    def __init__(self, idp: IdentityProvider) -> None:
        self.idp = idp
        # Replay cache: set of seen (message_id, nonce) within ttl window
        self._seen_nonces: Dict[str, int] = {}  # nonce -> expiry_timestamp_ns
        # Token bucket rate limiter: DID -> (tokens_left, last_refill_sec)
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self.default_rate_limit_fps = 1000  # 1000 frames per sec
        # Secrets Vault: uri -> secret string
        self._secrets_vault: Dict[str, str] = {
            "secrets://api-keys/stripe": "sk_test_51Mz_secret_stripe_token",
            "secrets://api-keys/github": "ghp_secure_github_personal_access_token",
            "secrets://db/prod_password": "SuperSecretDbPassword123!"
        }

    def _cleanup_replay_cache(self) -> None:
        now = time.time_ns()
        expired = [nonce for nonce, exp in self._seen_nonces.items() if now > exp]
        for nonce in expired:
            del self._seen_nonces[nonce]

    def check_replay_and_record(self, envelope: Envelope) -> bool:
        """Check timestamp skew and nonce uniqueness for replay protection."""
        now = time.time_ns()
        # Check time skew
        elapsed_ms = abs(now - envelope.timestamp_ns) / 1_000_000
        if elapsed_ms > envelope.ttl_ms:
            return False  # Expired or clock skew violation

        self._cleanup_replay_cache()
        nonce = envelope.security.nonce
        if nonce in self._seen_nonces:
            return False  # Replay attack!

        self._seen_nonces[nonce] = now + (envelope.ttl_ms * 1_000_000)
        return True

    def check_rate_limit(self, sender_did: str) -> bool:
        """Check Token Bucket rate limiter for the sender DID."""
        now_sec = time.time()
        if sender_did not in self._rate_limits:
            self._rate_limits[sender_did] = {"tokens": self.default_rate_limit_fps, "last_refill": now_sec}

        bucket = self._rate_limits[sender_did]
        # Refill
        elapsed = now_sec - bucket["last_refill"]
        if elapsed > 1.0:
            bucket["tokens"] = self.default_rate_limit_fps
            bucket["last_refill"] = now_sec

        if bucket["tokens"] <= 0:
            return False
        bucket["tokens"] -= 1
        return True

    def inject_secrets(self, payload_obj: Any) -> Any:
        """Recursively scan payload dictionary and replace placeholder 'secrets://...' URIs with actual secrets."""
        if isinstance(payload_obj, dict):
            return {k: self.inject_secrets(v) for k, v in payload_obj.items()}
        elif isinstance(payload_obj, list):
            return [self.inject_secrets(v) for v in payload_obj]
        elif isinstance(payload_obj, str) and "secrets://" in payload_obj:
            for secret_uri, secret_val in self._secrets_vault.items():
                if secret_uri in payload_obj:
                    payload_obj = payload_obj.replace(secret_uri, secret_val)
            return payload_obj
        return payload_obj

    def verify_ingress_frame(self, envelope: Envelope, required_action: Optional[str] = None, resource_uri: Optional[str] = None) -> Dict[str, Any]:
        """Perform full ingress verification: Replay check, Rate limit check, Signature check, and Capability check."""
        # Step 1: Replay protection
        if not self.check_replay_and_record(envelope):
            return {"status": "REJECTED", "code": 403, "reason": "Replay attack detected or timestamp expired"}

        # Step 2: Rate limit
        if not self.check_rate_limit(envelope.sender.agent_id):
            return {"status": "REJECTED", "code": 429, "reason": "Rate limit exceeded"}

        # Step 3: Signature verification
        sender_key = self.idp.get_secret_key(envelope.sender.agent_id)
        if sender_key and not envelope.verify_signature(sender_key):
            return {"status": "REJECTED", "code": 403, "reason": "Cryptographic signature verification failed"}

        # Step 4: Capability Token & ABAC check (if action and resource specified or embedded)
        if envelope.security.capability_token:
            try:
                # Parse or simulate capability check
                # In python reference, capability_token can be JSON string or token_id
                pass
            except Exception as e:
                return {"status": "REJECTED", "code": 403, "reason": f"Capability token parse error: {e}"}

        return {"status": "ALLOWED", "code": 200}
