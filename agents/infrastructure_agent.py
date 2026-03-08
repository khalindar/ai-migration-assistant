import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a cloud infrastructure architect. Based on the application analysis and the target cloud provider, identify all required cloud infrastructure resources.

Use the correct provider-specific service names:
- AWS: EKS, RDS, ElastiCache, ALB, SQS, S3, VPC, SecurityGroup, Subnet, IAM Role
- GCP: GKE, Cloud SQL, Memorystore, Cloud Load Balancing, Pub/Sub, Cloud Storage, VPC Network, Firewall Rule, Subnet, Service Account

Return JSON in exactly this format:
{
  "resources": [
    {"type": "<provider-specific type>", "name": "<resource-name>", "description": "<what it does>"}
  ],
  "network_topology": "description of the network design",
  "high_availability": true,
  "estimated_services_count": number
}
Always return at least 6 resources. Return only valid JSON, no markdown."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Identifying required infrastructure resources..."))
    log_queue.put(make_log("AI", f"Targeting cloud provider: {state.cloud_provider}"))

    analysis = state.repo_analysis
    deps = state.service_dependencies

    prompt = f"""Application details:
- Architecture: {analysis.get('architecture_pattern')}
- Services: {analysis.get('services')}
- Databases: {analysis.get('databases')}
- Message queues: {analysis.get('message_queues')}
- Cloud provider: {state.cloud_provider}
- Service dependencies: {list(deps.get('dependencies', {}).keys())}
- Data stores: {deps.get('data_stores', [])}
- External services: {deps.get('external_services', [])}

Identify all required infrastructure resources for deploying this application on {state.cloud_provider}."""

    raw = complete("infrastructure_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=2048)

    is_gcp = state.cloud_provider == "GCP"
    default_resources = (
        [
            {"type": "GKE", "name": "app-cluster", "description": "Managed Kubernetes cluster"},
            {"type": "Cloud SQL", "name": "postgres-db", "description": "Managed PostgreSQL database"},
            {"type": "Memorystore", "name": "redis-cache", "description": "Managed Redis cache"},
            {"type": "Cloud Load Balancing", "name": "app-lb", "description": "HTTP(S) load balancer"},
            {"type": "Pub/Sub", "name": "task-queue", "description": "Async messaging queue"},
            {"type": "Cloud Storage", "name": "app-assets", "description": "Object storage bucket"},
            {"type": "VPC Network", "name": "main-vpc", "description": "Primary virtual private cloud"},
            {"type": "Firewall Rule", "name": "app-fw", "description": "Ingress/egress firewall rules"},
            {"type": "Service Account", "name": "app-sa", "description": "Workload identity service account"},
        ] if is_gcp else [
            {"type": "EKS", "name": "app-cluster", "description": "Managed Kubernetes cluster"},
            {"type": "RDS", "name": "postgres-db", "description": "Managed PostgreSQL database"},
            {"type": "ElastiCache", "name": "redis-cache", "description": "Managed Redis cache"},
            {"type": "ALB", "name": "app-lb", "description": "Application load balancer"},
            {"type": "SQS", "name": "task-queue", "description": "Async task message queue"},
            {"type": "S3", "name": "app-assets", "description": "Static asset storage"},
            {"type": "VPC", "name": "main-vpc", "description": "Primary virtual private cloud"},
            {"type": "SecurityGroup", "name": "app-sg", "description": "Application security group"},
            {"type": "IAM Role", "name": "app-role", "description": "Application IAM role"},
        ]
    )

    data = extract_json(raw, fallback={"resources": default_resources})
    if not data.get("resources"):
        data["resources"] = default_resources

    state.infrastructure_plan = data
    state.terraform_resources = data.get("resources", [])

    resource_types = [r["type"] for r in state.terraform_resources]
    log_queue.put(make_log("AI", f"Infrastructure resources identified: {', '.join(set(resource_types))}", "info"))
    log_queue.put(make_log("AI", f"Total resources: {len(state.terraform_resources)}", "info"))
    log_queue.put(make_log("AI", "Infrastructure plan complete ✔", "success"))
    return state
