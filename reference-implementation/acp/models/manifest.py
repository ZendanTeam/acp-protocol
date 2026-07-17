"""Agent Manifest Pydantic Models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Skill(BaseModel):
    skill_id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    cost_credits_per_invocation: float = Field(default=0.0, ge=0.0)


class ModelSpec(BaseModel):
    model_id: str
    provider: str
    modality: List[str] = Field(default_factory=lambda: ["text"])
    context_window: Optional[int] = None


class Endpoint(BaseModel):
    transport: str
    url: str
    tls_required: bool = True


class SecurityProfile(BaseModel):
    supported_auth: List[str] = Field(default_factory=lambda: ["CAPABILITY_TOKEN", "JWT"])
    sandboxed: bool = True
    isolation_level: str = "CONTAINER"
    pubkey_base64: Optional[str] = None


class ResourceRequirements(BaseModel):
    min_cpu_cores: Optional[float] = None
    min_ram_mb: Optional[int] = None
    gpu_required: bool = False
    memory_tier: str = "ALL"


class AgentManifest(BaseModel):
    did: str = Field(..., pattern=r"^did:acp:[a-zA-Z0-9_:-]+$")
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    author: Optional[Dict[str, str]] = None
    skills: List[Skill] = Field(default_factory=list)
    models: List[ModelSpec] = Field(default_factory=list)
    endpoints: List[Endpoint] = Field(default_factory=list)
    security_profile: SecurityProfile = Field(default_factory=SecurityProfile)
    resource_requirements: ResourceRequirements = Field(default_factory=ResourceRequirements)
