import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a cloud cost analyst. Estimate monthly cloud infrastructure costs.
Return JSON:
{
  "provider": "AWS or GCP",
  "region": "us-east-1 or us-central1",
  "line_items": [
    {"resource": "EKS Cluster", "type": "Compute", "qty": 1, "unit": "cluster", "unit_cost": 144, "monthly_cost": 144},
    {"resource": "EC2 Nodes (t3.medium x3)", "type": "Compute", "qty": 3, "unit": "instance", "unit_cost": 30, "monthly_cost": 90},
    {"resource": "RDS PostgreSQL (db.t3.medium)", "type": "Database", "qty": 1, "unit": "instance", "unit_cost": 60, "monthly_cost": 60},
    {"resource": "ElastiCache Redis (cache.t3.micro)", "type": "Cache", "qty": 1, "unit": "node", "unit_cost": 15, "monthly_cost": 15},
    {"resource": "Application Load Balancer", "type": "Networking", "qty": 1, "unit": "ALB", "unit_cost": 18, "monthly_cost": 18},
    {"resource": "S3 Storage (100GB)", "type": "Storage", "qty": 100, "unit": "GB", "unit_cost": 0.023, "monthly_cost": 2.3},
    {"resource": "Data Transfer", "type": "Networking", "qty": 1, "unit": "TB", "unit_cost": 90, "monthly_cost": 90}
  ],
  "subtotal": 419.3,
  "tax_estimate": 33.5,
  "total_monthly": 452.8,
  "total_annual": 5433.6,
  "cost_breakdown_by_category": {
    "Compute": 234,
    "Database": 60,
    "Cache": 15,
    "Networking": 108,
    "Storage": 2.3
  },
  "savings_recommendations": [
    "Use Reserved Instances for 30-40% savings",
    "Enable S3 Intelligent Tiering"
  ],
  "currency": "USD"
}
Return only valid JSON with realistic cost estimates."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating financial cost estimation..."))
    log_queue.put(make_log("AI", f"Calculating costs for {state.cloud_provider} deployment..."))

    resources_text = "\n".join([
        f"- {r['type']}: {r['name']}"
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
        data = _fallback_cost()

    state.cost_estimation = data
    total = data.get("total_monthly", 0)

    log_queue.put(make_log("AI", f"Estimated monthly cost: ${total:,.2f}", "info"))
    log_queue.put(make_log("AI", f"Estimated annual cost: ${data.get('total_annual', total * 12):,.2f}", "info"))
    log_queue.put(make_log("AI", "Cost estimation complete ✔", "success"))
    return state


def _fallback_cost() -> dict:
    return {
        "provider": "AWS",
        "region": "us-east-1",
        "line_items": [
            {"resource": "EKS Cluster", "type": "Compute", "qty": 1, "unit": "cluster", "unit_cost": 144, "monthly_cost": 144},
            {"resource": "EC2 Nodes (t3.medium x2)", "type": "Compute", "qty": 2, "unit": "instance", "unit_cost": 30, "monthly_cost": 60},
            {"resource": "RDS PostgreSQL", "type": "Database", "qty": 1, "unit": "instance", "unit_cost": 60, "monthly_cost": 60},
            {"resource": "Application Load Balancer", "type": "Networking", "qty": 1, "unit": "ALB", "unit_cost": 18, "monthly_cost": 18},
        ],
        "subtotal": 282,
        "tax_estimate": 22.6,
        "total_monthly": 304.6,
        "total_annual": 3655.2,
        "cost_breakdown_by_category": {"Compute": 204, "Database": 60, "Networking": 18},
        "savings_recommendations": ["Use Reserved Instances for 30-40% savings"],
        "currency": "USD",
    }
