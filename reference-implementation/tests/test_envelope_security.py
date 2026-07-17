"""Tests for Envelope Cryptographic Signing, Replay Protection, Rate Limiting, and Capability Tokens."""
import time
import pytest
from acp.models.envelope import Envelope, Sender, Receiver, TargetType, FrameType
from acp.models.capability import CapabilityToken, CapabilityClaim
from acp.services.identity import IdentityProvider
from acp.services.security import SecurityEngine


def test_envelope_canonicalization_and_signing():
    sender = Sender(agent_id="did:acp:test:sender", host_id="host_1")
    receiver = Receiver(target_type=TargetType.AGENT, target_id="did:acp:test:receiver")
    envelope = Envelope(
        sender=sender,
        receiver=receiver,
        frame_type=FrameType.REQUEST,
        payload={"action": "test", "val": 42}
    )
    
    secret = "my_super_secret_key"
    sig = envelope.sign(secret)
    assert sig is not None
    assert envelope.verify_signature(secret) is True
    assert envelope.verify_signature("wrong_secret") is False


def test_replay_protection():
    idp = IdentityProvider()
    sec = SecurityEngine(idp)
    sender = Sender(agent_id="did:acp:test:sender", host_id="host_1")
    receiver = Receiver(target_type=TargetType.AGENT, target_id="did:acp:test:receiver")
    
    envelope = Envelope(
        sender=sender,
        receiver=receiver,
        frame_type=FrameType.REQUEST,
        payload={"action": "transfer"}
    )
    
    # First check should succeed and record nonce
    assert sec.check_replay_and_record(envelope) is True
    # Second check with identical nonce must fail
    assert sec.check_replay_and_record(envelope) is False


def test_rate_limiting():
    idp = IdentityProvider()
    sec = SecurityEngine(idp)
    sec.default_rate_limit_fps = 3  # Set limit to 3 frames per sec for test
    
    did = "did:acp:test:rate-limited"
    assert sec.check_rate_limit(did) is True
    assert sec.check_rate_limit(did) is True
    assert sec.check_rate_limit(did) is True
    # 4th request must be rate limited
    assert sec.check_rate_limit(did) is False


def test_secrets_injection():
    idp = IdentityProvider()
    sec = SecurityEngine(idp)
    
    payload = {
        "api_endpoint": "https://api.stripe.com/v1/charges",
        "auth_header": "Bearer secrets://api-keys/stripe",
        "nested": {"key": "secrets://db/prod_password"}
    }
    
    injected = sec.inject_secrets(payload)
    assert injected["auth_header"] == "Bearer sk_test_51Mz_secret_stripe_token"
    assert injected["nested"]["key"] == "SuperSecretDbPassword123!"


def test_capability_token_lifecycle():
    idp = IdentityProvider()
    secret = idp.register_did("did:acp:org:admin")
    
    claims = [
        CapabilityClaim(resource="memory://long-term/financial/*", actions=["READ", "WRITE"]),
        CapabilityClaim(resource="agent://did:acp:org:db/execute", actions=["EXECUTE"])
    ]
    
    token = idp.issue_capability_token("did:acp:org:admin", "did:acp:org:worker", claims, ttl_seconds=60)
    assert idp.verify_capability_token(token) is True
    
    # Check valid resource action
    assert token.is_valid_for("READ", "memory://long-term/financial/report_2026.json") is True
    assert token.is_valid_for("DELETE", "memory://long-term/financial/report_2026.json") is False
    assert token.is_valid_for("READ", "memory://long-term/hr/salaries.json") is False
