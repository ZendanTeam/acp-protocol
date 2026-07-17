"""Universal ACP Frame Envelope Pydantic Models and Cryptographic Utilities."""
import json
import time
import uuid
import hmac
import hashlib
import base64
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TargetType(str, Enum):
    AGENT = "AGENT"
    CLUSTER = "CLUSTER"
    TOPIC = "TOPIC"
    BROKER = "BROKER"
    SCHEDULER = "SCHEDULER"
    MEMORY = "MEMORY"
    DISCOVERY = "DISCOVERY"
    HUMAN = "HUMAN"
    TOOL = "TOOL"
    DATABASE = "DATABASE"
    ROBOT = "ROBOT"
    API = "API"
    BROWSER = "BROWSER"


class FrameType(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    STREAM_CHUNK = "STREAM_CHUNK"
    STREAM_END = "STREAM_END"
    EVENT = "EVENT"
    NEGOTIATION_PROPOSAL = "NEGOTIATION_PROPOSAL"
    NEGOTIATION_COUNTER = "NEGOTIATION_COUNTER"
    NEGOTIATION_ACCEPT = "NEGOTIATION_ACCEPT"
    NEGOTIATION_REJECT = "NEGOTIATION_REJECT"
    VOTE_CAST = "VOTE_CAST"
    TASK_DELEGATION = "TASK_DELEGATION"
    TASK_STATUS = "TASK_STATUS"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"


class Sender(BaseModel):
    agent_id: str = Field(..., pattern=r"^did:acp:[a-zA-Z0-9_:-]+$")
    host_id: str
    instance_id: Optional[str] = None
    pubkey: Optional[str] = None


class Receiver(BaseModel):
    target_type: TargetType
    target_id: Optional[str] = None
    routing_query: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_target_or_query(self) -> "Receiver":
        if not self.target_id and not self.routing_query:
            raise ValueError("Receiver must provide either 'target_id' or 'routing_query'")
        return self


class Routing(BaseModel):
    hop_count: int = Field(default=0, ge=0)
    max_hops: int = Field(default=16, ge=1)
    reply_to: Optional[str] = None
    trace_parent: Optional[str] = None
    router_path: List[str] = Field(default_factory=list)


class Security(BaseModel):
    auth_token: Optional[str] = None
    capability_token: Optional[str] = None
    nonce: str = Field(default_factory=lambda: uuid.uuid4().hex)
    signature: Optional[str] = None
    signature_alg: str = Field(default="HMAC-SHA256")
    encryption_alg: str = Field(default="NONE")
    encrypted_key: Optional[str] = None


class Envelope(BaseModel):
    acp_version: str = Field(default="1.0.0")
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    timestamp_ns: int = Field(default_factory=lambda: int(time.time_ns()))
    ttl_ms: int = Field(default=30000, ge=1)
    sender: Sender
    receiver: Receiver
    frame_type: FrameType
    routing: Routing = Field(default_factory=Routing)
    security: Security = Field(default_factory=Security)
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_canonical_json(self) -> str:
        """Serialize envelope fields (excluding signature) deterministically for cryptographic signing."""
        data = {
            "acp_version": self.acp_version,
            "message_id": self.message_id,
            "timestamp_ns": self.timestamp_ns,
            "sender": self.sender.model_dump(exclude_none=True),
            "receiver": self.receiver.model_dump(exclude_none=True),
            "frame_type": self.frame_type.value,
            "nonce": self.security.nonce,
            "payload": self.payload
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def sign(self, secret_key: str) -> str:
        """Sign the canonical envelope using HMAC-SHA256 (or simulated Ed25519 using base64 key)."""
        canonical = self.to_canonical_json().encode("utf-8")
        sig_bytes = hmac.new(secret_key.encode("utf-8"), canonical, hashlib.sha256).digest()
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
        self.security.signature = sig_b64
        return sig_b64

    def verify_signature(self, secret_key: str) -> bool:
        """Verify the signature embedded in security.signature against the given secret key."""
        if not self.security.signature:
            return False
        canonical = self.to_canonical_json().encode("utf-8")
        expected_bytes = hmac.new(secret_key.encode("utf-8"), canonical, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(expected_bytes).decode("utf-8")
        return hmac.compare_digest(self.security.signature, expected_b64)

    def is_expired(self, current_time_ns: Optional[int] = None) -> bool:
        """Check if the frame TTL has been exceeded."""
        if current_time_ns is None:
            current_time_ns = time.time_ns()
        elapsed_ms = (current_time_ns - self.timestamp_ns) / 1_000_000
        return elapsed_ms > self.ttl_ms
