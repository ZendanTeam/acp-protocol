"""ACP Agent Runtime and Sandboxed Execution Wrapper."""
from typing import Dict, Any, Callable, Optional, List, Generator
from acp.models.manifest import AgentManifest
from acp.models.envelope import Envelope, FrameType, TargetType
from acp.services.memory import MemoryService, MemoryTier, MemoryOperation, MemoryOperationPayload


class AgentRuntime:
    """Sandboxed Execution Unit for an autonomous ACP Agent."""

    def __init__(self, manifest: AgentManifest, memory_service: MemoryService, host_id: str) -> None:
        self.manifest = manifest
        self.did = manifest.did
        self.memory_service = memory_service
        self.host_id = host_id
        # Skill handlers: skill_id -> callable taking (parameters, memory_service, session_id) -> result dict or Generator
        self.skill_handlers: Dict[str, Callable[..., Any]] = {}

    def register_skill_handler(self, skill_id: str, handler: Callable[..., Any]) -> None:
        """Register a Python callback handler for a declared skill."""
        self.skill_handlers[skill_id] = handler

    def handle_ingress_frame(self, envelope: Envelope) -> Optional[Envelope]:
        """Dispatch incoming envelope to the appropriate skill handler or respond to heartbeats."""
        if envelope.frame_type == FrameType.HEARTBEAT:
            return Envelope(
                sender={"agent_id": self.did, "host_id": self.host_id},
                receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                frame_type=FrameType.RESPONSE,
                correlation_id=envelope.message_id,
                payload={"status": "ALIVE", "version": self.manifest.version}
            )

        if envelope.frame_type == FrameType.REQUEST:
            action = envelope.payload.get("action")
            parameters = envelope.payload.get("parameters", {})
            session_id = envelope.correlation_id or envelope.message_id

            if not action or action not in self.skill_handlers:
                return Envelope(
                    sender={"agent_id": self.did, "host_id": self.host_id},
                    receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                    frame_type=FrameType.ERROR,
                    correlation_id=envelope.message_id,
                    payload={"error": {"code": "404", "message": f"Skill action '{action}' not supported by {self.did}"}}
                )

            try:
                handler = self.skill_handlers[action]
                result = handler(parameters, self.memory_service, session_id)
                # Check if generator (streaming response)
                if isinstance(result, Generator):
                    # For sync return, we collect generator or return first chunk (in async stream this yields chunks)
                    chunks = list(result)
                    return Envelope(
                        sender={"agent_id": self.did, "host_id": self.host_id},
                        receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                        frame_type=FrameType.RESPONSE,
                        correlation_id=envelope.message_id,
                        payload={"status": "SUCCESS", "result": {"chunks": chunks, "streamed": True}}
                    )

                return Envelope(
                    sender={"agent_id": self.did, "host_id": self.host_id},
                    receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                    frame_type=FrameType.RESPONSE,
                    correlation_id=envelope.message_id,
                    payload={"status": "SUCCESS", "result": result}
                )
            except Exception as e:
                return Envelope(
                    sender={"agent_id": self.did, "host_id": self.host_id},
                    receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                    frame_type=FrameType.ERROR,
                    correlation_id=envelope.message_id,
                    payload={"error": {"code": "500", "message": f"Execution failed: {str(e)}"}}
                )

        return None
