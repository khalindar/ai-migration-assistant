import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log


SYSTEM = """You are a Kubernetes expert. Generate production-ready Kubernetes YAML manifests.
Return a JSON object where keys are service names and values are the complete YAML string for that service.
Include Deployment, Service, and where appropriate HorizontalPodAutoscaler.
Format:
{
  "services": ["ServiceA", "ServiceB"],
  "manifests": {
    "ServiceA": "apiVersion: apps/v1\\nkind: Deployment\\n...",
    "ServiceB": "apiVersion: apps/v1\\nkind: Deployment\\n...",
    "ingress": "apiVersion: networking.k8s.io/v1\\nkind: Ingress\\n..."
  },
  "namespace": "app-production",
  "cluster_type": "EKS or GKE"
}
Return only valid JSON."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating Kubernetes deployment manifests..."))
    log_queue.put(make_log("AI", f"Targeting {'EKS' if state.cloud_provider == 'AWS' else 'GKE'} cluster"))

    cluster = "EKS" if state.cloud_provider == "AWS" else "GKE"
    services = state.detected_services or ["api-service", "frontend"]
    deps = state.service_dependencies.get("dependencies", {})

    prompt = f"""Application services to deploy:
{', '.join(services)}

Architecture pattern: {state.architecture_pattern}
Cloud provider: {state.cloud_provider}
Cluster type: {cluster}
Dependencies: {deps}

Generate Kubernetes YAML manifests for all services.
Use namespace: app-production
Include resource limits, liveness/readiness probes, and environment variable placeholders."""

    from utils.json_parser import extract_json
    raw = complete("kubernetes_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=8096)
    data = extract_json(raw, fallback={"manifests": {}, "services": services})

    state.kubernetes_manifests = data
    manifest_count = len(data.get("manifests", {}))

    log_queue.put(make_log("AI", f"Generated {manifest_count} Kubernetes manifests", "info"))
    log_queue.put(make_log("AI", f"Namespace: {data.get('namespace', 'app-production')}", "info"))
    log_queue.put(make_log("AI", "Kubernetes manifests ready ✔", "success"))
    return state
