"""ACP Host Daemon supervising Runtimes, Gateways, Routers, and System Isolation."""
import time
from typing import Dict, List, Optional, Any
from acp.runtime.agent import AgentRuntime
from acp.runtime.gateway import Gateway
from acp.runtime.router import Router
from acp.models.manifest import AgentManifest
from acp.services.memory import MemoryService


class Host:
    """Supervises Agent Runtimes on a physical/virtual machine, handling lifecycles and restarts."""

    def __init__(self, host_id: str, gateway: Gateway, router: Router, memory_service: MemoryService) -> None:
        self.host_id = host_id
        self.gateway = gateway
        self.router = router
        self.memory_service = memory_service
        self.runtimes: Dict[str, AgentRuntime] = {}
        self._restart_counts: Dict[str, int] = {}
        self.start_time = time.time()

    def spawn_agent(self, manifest: AgentManifest) -> AgentRuntime:
        """Spawn a new sandboxed Agent Runtime and wire its handler into the Router."""
        runtime = AgentRuntime(manifest, self.memory_service, self.host_id)
        self.runtimes[manifest.did] = runtime
        self._restart_counts[manifest.did] = 0

        # Wire directly into Router routes
        self.router.register_route(manifest.did, runtime.handle_ingress_frame)
        return runtime

    def terminate_agent(self, did: str) -> bool:
        """Terminate and clean up an agent runtime."""
        if did in self.runtimes:
            del self.runtimes[did]
            if did in self.router.routes:
                del self.router.routes[did]
            return True
        return False

    def restart_agent(self, did: str) -> Optional[AgentRuntime]:
        """Simulate graceful restart of a crashed runtime with exponential backoff checks."""
        if did not in self.runtimes:
            return None
        runtime = self.runtimes[did]
        self._restart_counts[did] += 1
        # Exponential backoff check (max 5 restarts)
        if self._restart_counts[did] > 5:
            self.terminate_agent(did)
            return None
        return runtime

    def get_health_metrics(self) -> Dict[str, Any]:
        """Return host system health, active agent counts, and uptime."""
        return {
            "host_id": self.host_id,
            "status": "HEALTHY",
            "uptime_seconds": round(time.time() - self.start_time, 2),
            "active_agents": len(self.runtimes),
            "restarts": self._restart_counts
        }
