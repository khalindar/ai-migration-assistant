import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log


SYSTEM = """You are a Kubernetes expert. Generate production-ready Kubernetes YAML manifests.
Return a JSON object in exactly this format. YAML values must use \\n for newlines (no literal newlines inside JSON strings).
Do NOT include cloud-provider-specific annotations or CRDs — use only standard Kubernetes resources.
{
  "services": ["ServiceA", "ServiceB"],
  "manifests": {
    "ServiceA": "apiVersion: apps/v1\\nkind: Deployment\\nmetadata:\\n  name: servicea\\n  namespace: app-production\\nspec:\\n  replicas: 2\\n  selector:\\n    matchLabels:\\n      app: servicea\\n  template:\\n    metadata:\\n      labels:\\n        app: servicea\\n    spec:\\n      containers:\\n      - name: servicea\\n        image: servicea:latest\\n        ports:\\n        - containerPort: 8080",
    "ingress": "apiVersion: networking.k8s.io/v1\\nkind: Ingress\\nmetadata:\\n  name: app-ingress\\n  namespace: app-production\\nspec:\\n  rules:\\n  - http:\\n      paths:\\n      - path: /\\n        pathType: Prefix\\n        backend:\\n          service:\\n            name: servicea\\n            port:\\n              number: 80"
  },
  "namespace": "app-production",
  "cluster_type": "EKS or GKE"
}
Return only valid JSON, no markdown fences."""


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
    fallback_manifests = {
        svc: (
            f"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {svc.lower()}\n"
            f"  namespace: app-production\nspec:\n  replicas: 2\n  selector:\n"
            f"    matchLabels:\n      app: {svc.lower()}\n  template:\n    metadata:\n"
            f"      labels:\n        app: {svc.lower()}\n    spec:\n      containers:\n"
            f"      - name: {svc.lower()}\n        image: {svc.lower()}:latest\n"
            f"        ports:\n        - containerPort: 8080"
        )
        for svc in services[:4]
    }
    data = extract_json(raw, fallback={"manifests": fallback_manifests, "services": services})
    if not data.get("manifests"):
        data["manifests"] = fallback_manifests

    state.kubernetes_manifests = data
    manifest_count = len(data.get("manifests", {}))

    log_queue.put(make_log("AI", f"Generated {manifest_count} Kubernetes manifests", "info"))
    log_queue.put(make_log("AI", f"Namespace: {data.get('namespace', 'app-production')}", "info"))
    log_queue.put(make_log("AI", "Kubernetes manifests ready ✔", "success"))
    return state
