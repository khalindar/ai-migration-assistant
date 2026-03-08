import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a cloud infrastructure architect. Based on the application analysis, identify all required cloud infrastructure resources.
Return JSON in this format:
{
  "resources": [
    {"type": "VPC", "name": "main-vpc", "description": "Primary virtual private cloud"},
    {"type": "EKS", "name": "app-cluster", "description": "Managed Kubernetes cluster"},
    {"type": "RDS", "name": "postgres-db", "description": "PostgreSQL managed database"},
    {"type": "ElastiCache", "name": "redis-cache", "description": "Redis cache cluster"},
    {"type": "ALB", "name": "app-lb", "description": "Application load balancer"},
    {"type": "SQS", "name": "task-queue", "description": "Async task message queue"},
    {"type": "S3", "name": "app-assets", "description": "Static asset storage"},
    {"type": "Subnet", "name": "public-subnet", "description": "Public subnet"},
    {"type": "Subnet", "name": "private-subnet", "description": "Private subnet"},
    {"type": "SecurityGroup", "name": "app-sg", "description": "Application security group"}
  ],
  "network_topology": "description of the network design",
  "high_availability": true or false,
  "estimated_services_count": number
}
Return only valid JSON."""


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

    data = extract_json(raw, fallback={"resources": []})

    state.infrastructure_plan = data
    state.terraform_resources = data.get("resources", [])

    resource_types = [r["type"] for r in state.terraform_resources]
    log_queue.put(make_log("AI", f"Infrastructure resources identified: {', '.join(set(resource_types))}", "info"))
    log_queue.put(make_log("AI", f"Total resources: {len(state.terraform_resources)}", "info"))
    log_queue.put(make_log("AI", "Infrastructure plan complete ✔", "success"))
    return state
