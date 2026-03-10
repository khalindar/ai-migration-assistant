from typing import Any, Optional
from pydantic import BaseModel, Field


class StepStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


WORKFLOW_STEPS = [
    {"id": "scan",           "label": "Scanning repository",                          "agent": "RepoScannerAgent",      "model": "Sonnet"},
    {"id": "analyze",        "label": "Analyzing repository structure",               "agent": "RepoAnalysisAgent",     "model": "Sonnet"},
    {"id": "summarize",      "label": "Summarizing repository architecture",          "agent": "RepoSummaryAgent",      "model": "Sonnet"},
    {"id": "dependencies",   "label": "Generating service dependency graph",          "agent": "DependencyAgent",       "model": "Sonnet"},
    {"id": "infrastructure", "label": "Generating required infrastructure resources", "agent": "InfrastructureAgent",   "model": "Sonnet"},
    {"id": "modernization",  "label": "Creating modernization plan for cloud migration","agent": "ModernizationAgent",  "model": "Opus"},
    {"id": "cloud",          "label": "Identifying optimal cloud provider",           "agent": "CloudSelectionAgent",   "model": "Sonnet"},
    {"id": "kubernetes",     "label": "Generating Kubernetes deployment YAML",        "agent": "KubernetesAgent",       "model": "Sonnet"},
    {"id": "terraform",      "label": "Generating Terraform infrastructure",          "agent": "TerraformAgent",        "model": "Sonnet"},
    {"id": "bundle",         "label": "Bundling application code for deployment",     "agent": "DeploymentAgent",       "model": "Sonnet"},
    {"id": "provision",      "label": "Simulating Terraform provisioning",            "agent": "DeploymentAgent",       "model": "Sonnet"},
    {"id": "deploy",         "label": "Publishing application to Kubernetes cluster", "agent": "DeploymentAgent",       "model": "Sonnet"},
    {"id": "validate",       "label": "Validating public application URL",            "agent": "DeploymentAgent",       "model": "Sonnet"},
    {"id": "cost",           "label": "Generating financial cost estimation",         "agent": "CostEstimationAgent",   "model": "Sonnet"},
]


class PlatformState(BaseModel):
    # Input
    repo_url: str = ""
    safe_mode: bool = True
    cloud_provider: str = "AWS"
    TUMI_dependency: bool = False

    # Step statuses
    step_statuses: dict[str, str] = Field(
        default_factory=lambda: {s["id"]: StepStatus.PENDING for s in WORKFLOW_STEPS}
    )

    # Workflow control
    workflow_running: bool = False
    workflow_complete: bool = False
    workflow_error: Optional[str] = None

    # Agent outputs
    repo_structure: dict = Field(default_factory=dict)
    repo_analysis: dict = Field(default_factory=dict)
    repo_summary: str = ""
    service_dependencies: dict = Field(default_factory=dict)
    infrastructure_plan: dict = Field(default_factory=dict)
    modernization_plan: dict = Field(default_factory=dict)
    kubernetes_manifests: dict = Field(default_factory=dict)
    terraform_code: str = ""
    terraform_resources: list = Field(default_factory=list)
    deployment_status: dict = Field(default_factory=dict)
    cost_estimation: dict = Field(default_factory=dict)
    simulated_endpoint: str = ""

    # Diagram data
    mermaid_diagram: str = ""
    dependency_graph_data: dict = Field(default_factory=dict)

    # Persistence metadata
    loaded_from_cache: bool = False

    # Detected metadata
    detected_services: list = Field(default_factory=list)
    detected_languages: list = Field(default_factory=list)
    detected_frameworks: list = Field(default_factory=list)
    architecture_pattern: str = ""

    class Config:
        arbitrary_types_allowed = True
