import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a cloud cost analyst. Estimate monthly cloud infrastructure costs for the specified provider.

For AWS use services like: EKS, EC2, RDS, ElastiCache, ALB, S3, CloudWatch.
For GCP use services like: GKE, Compute Engine, Cloud SQL, Memorystore, Cloud Load Balancing, Cloud Storage, Cloud Monitoring.

Return JSON in exactly this format:
{
  "provider": "AWS or GCP",
  "region": "us-east-1 or us-central1",
  "line_items": [
    {"resource": "<provider-specific resource name>", "type": "Compute", "qty": 1, "unit": "cluster", "unit_cost": 150, "monthly_cost": 150}
  ],
  "total_monthly": 500,
  "total_annual": 6000,
  "cost_breakdown_by_category": {
    "Compute": 300,
    "Database": 100,
    "Networking": 50,
    "Storage": 50
  },
  "savings_recommendations": [
    "Use committed use discounts for 30-40% savings"
  ],
  "currency": "USD"
}
Return only valid JSON with realistic cost estimates for the specified cloud provider."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating financial cost estimation..."))
    log_queue.put(make_log("AI", f"Calculating costs for {state.cloud_provider} deployment..."))

    resources_text = "\n".join([
        f"- {r.get('type', 'Resource')}: {r.get('name', 'unnamed')}"
        for r in state.terraform_resources
    ])

    prompt = f"""Cloud provider: {state.cloud_provider}
Services to deploy: {', '.join(state.detected_services)}
Infrastructure resources:
{resources_text}

Architecture complexity: {state.repo_analysis.get('complexity', 'medium')}

Generate a detailed monthly cost estimation for this deployment."""

    raw = complete("cost_estimation_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=2048)

    data = extract_json(raw, fallback=None)
    if not data:
        data = _fallback_cost(state.cloud_provider)

    state.cost_estimation = data
    total = data.get("total_monthly", 0)

    log_queue.put(make_log("AI", f"Estimated monthly cost: ${total:,.2f}", "info"))
    log_queue.put(make_log("AI", f"Estimated annual cost: ${data.get('total_annual', total * 12):,.2f}", "info"))
    log_queue.put(make_log("AI", "Cost estimation complete ✔", "success"))
    return state


def _fallback_cost(provider: str = "AWS") -> dict:
    if provider == "GCP":
        return {
            "provider": "GCP",
            "region": "us-central1",
            "line_items": [
                {"resource": "GKE Cluster", "type": "Compute", "qty": 1, "unit": "cluster", "unit_cost": 72, "monthly_cost": 72},
                {"resource": "Compute Engine (n2-standard-2 x2)", "type": "Compute", "qty": 2, "unit": "instance", "unit_cost": 48, "monthly_cost": 96},
                {"resource": "Cloud SQL (PostgreSQL db-n1-standard-1)", "type": "Database", "qty": 1, "unit": "instance", "unit_cost": 55, "monthly_cost": 55},
                {"resource": "Memorystore Redis (1GB)", "type": "Cache", "qty": 1, "unit": "node", "unit_cost": 16, "monthly_cost": 16},
                {"resource": "Cloud Load Balancing", "type": "Networking", "qty": 1, "unit": "LB", "unit_cost": 18, "monthly_cost": 18},
                {"resource": "Cloud Storage (100GB)", "type": "Storage", "qty": 100, "unit": "GB", "unit_cost": 0.02, "monthly_cost": 2},
            ],
            "total_monthly": 259,
            "total_annual": 3108,
            "cost_breakdown_by_category": {"Compute": 168, "Database": 55, "Cache": 16, "Networking": 18, "Storage": 2},
            "savings_recommendations": ["Use committed use discounts for 30-40% savings", "Enable Cloud Storage lifecycle policies"],
            "currency": "USD",
        }
    return {
        "provider": "AWS",
        "region": "us-east-1",
        "line_items": [
            {"resource": "EKS Cluster", "type": "Compute", "qty": 1, "unit": "cluster", "unit_cost": 144, "monthly_cost": 144},
            {"resource": "EC2 Nodes (t3.medium x2)", "type": "Compute", "qty": 2, "unit": "instance", "unit_cost": 30, "monthly_cost": 60},
            {"resource": "RDS PostgreSQL", "type": "Database", "qty": 1, "unit": "instance", "unit_cost": 60, "monthly_cost": 60},
            {"resource": "Application Load Balancer", "type": "Networking", "qty": 1, "unit": "ALB", "unit_cost": 18, "monthly_cost": 18},
            {"resource": "ElastiCache Redis", "type": "Cache", "qty": 1, "unit": "node", "unit_cost": 15, "monthly_cost": 15},
            {"resource": "S3 Storage (100GB)", "type": "Storage", "qty": 100, "unit": "GB", "unit_cost": 0.023, "monthly_cost": 3},
        ],
        "total_monthly": 300,
        "total_annual": 3600,
        "cost_breakdown_by_category": {"Compute": 204, "Database": 60, "Networking": 18, "Cache": 15, "Storage": 3},
        "savings_recommendations": ["Use Reserved Instances for 30-40% savings", "Enable S3 Intelligent Tiering"],
        "currency": "USD",
    }
