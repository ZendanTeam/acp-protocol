"""ACP Router Implementation for Mesh Routing, Skill Discovery Routing, and Multicast."""
from typing import Dict, Optional, Callable, Any, List
from acp.models.envelope import Envelope, TargetType, FrameType
from acp.services.discovery import DiscoveryService
from acp.transport.event_bus import EventBus


class Router:
    """Mesh Router enforcing hop counts, loop detection, and dynamic skill/capability routing."""

    def __init__(self, router_id: str, discovery: DiscoveryService, event_bus: EventBus) -> None:
        self.router_id = router_id
        self.discovery = discovery
        self.event_bus = event_bus
        # Direct routing table: target_id -> callback/handler
        self.routes: Dict[str, Callable[[Envelope], Optional[Envelope]]] = {}

    def register_route(self, target_id: str, handler: Callable[[Envelope], Optional[Envelope]]) -> None:
        """Register a direct handler for a target DID or endpoint."""
        self.routes[target_id] = handler

    def route_frame(self, envelope: Envelope) -> Optional[Envelope]:
        """Route an incoming envelope to its destination agent, topic, or cluster."""
        # 1. Hop count check and append router path
        envelope.routing.hop_count += 1
        if envelope.routing.hop_count > envelope.routing.max_hops:
            # Routing loop or TTL exceeded
            error_env = Envelope(
                sender={"agent_id": f"did:acp:router:{self.router_id}", "host_id": self.router_id},
                receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
                frame_type=FrameType.ERROR,
                payload={"error": {"code": "508", "message": "Loop Detected / Max Hops Exceeded"}}
            )
            return error_env

        envelope.routing.router_path.append(self.router_id)

        target_type = envelope.receiver.target_type
        target_id = envelope.receiver.target_id

        # 2. Topic Pub/Sub Routing
        if target_type == TargetType.TOPIC and target_id:
            self.event_bus.publish(target_id, envelope)
            return None

        # 3. Direct DID Routing
        if target_id and target_id in self.routes:
            return self.routes[target_id](envelope)

        # 4. Skill/Capability-Based Dynamic Routing (if target_id is omitted or query provided)
        if not target_id and envelope.receiver.routing_query:
            candidate_manifests = self.discovery.search_by_query(envelope.receiver.routing_query)
            if not candidate_manifests:
                # Try search by required_skill if string
                req_skill = envelope.receiver.routing_query.get("skill_id")
                if req_skill:
                    candidate_manifests = self.discovery.search_by_skill(req_skill)

            if candidate_manifests:
                # Pick best candidate (first or cheapest)
                best_did = candidate_manifests[0].did
                envelope.receiver.target_id = best_did
                if best_did in self.routes:
                    return self.routes[best_did](envelope)

        # 5. Fallback: Publish on Event Bus under direct address topic
        if target_id:
            delivered = self.event_bus.publish(f"acp.agents.{target_id}", envelope)
            if delivered > 0:
                return None

        # Route Not Found
        return Envelope(
            sender={"agent_id": f"did:acp:router:{self.router_id}", "host_id": self.router_id},
            receiver={"target_type": TargetType.AGENT, "target_id": envelope.sender.agent_id},
            frame_type=FrameType.ERROR,
            payload={"error": {"code": "404", "message": f"Target endpoint {target_id} not found via Router {self.router_id}"}}
        )
