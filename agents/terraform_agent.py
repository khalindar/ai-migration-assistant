import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log


SYSTEM = """You are a Terraform expert. Generate complete, production-ready Terraform HCL code.
Return ONLY raw HCL code. Do NOT wrap in JSON. Do NOT use markdown fences.
Start directly with the terraform block.
Structure the code with clearly labelled sections using comments like:
# =====================
# Provider Configuration
# =====================
...HCL...

# =====================
# Networking
# =====================
...HCL...

Include: provider config, VPC/networking, cluster, database, cache, load balancer, storage, IAM, variables, outputs."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating Terraform infrastructure code..."))
    log_queue.put(make_log("AI", f"Target: {state.cloud_provider} — {len(state.terraform_resources)} resources"))

    resources_summary = "\n".join([
        f"- {r.get('type', '')}: {r.get('name', '')} — {r.get('description', '')}"
        for r in state.terraform_resources
    ])

    provider = "aws" if state.cloud_provider == "AWS" else "google"
    cluster_type = "EKS" if state.cloud_provider == "AWS" else "GKE"

    prompt = f"""Generate Terraform HCL for the following infrastructure.

Cloud provider: {state.cloud_provider}
Terraform provider: {provider}
Cluster type: {cluster_type}
Application services: {', '.join(state.detected_services)}
Architecture: {state.architecture_pattern}

Infrastructure resources to provision:
{resources_summary}

Requirements:
- Use {provider} provider with region variable
- Include proper IAM roles and policies
- Add tags/labels on all resources
- Use variables for environment, region, cluster name
- Include outputs for key resource IDs and endpoints
- Make it production-ready with proper naming conventions

Return ONLY valid HCL code, no markdown, no JSON."""

    raw = complete("terraform_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=8096)

    # Strip any accidental markdown fences
    code = raw.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    state.terraform_code = code.strip()

    module_count = state.terraform_code.count("# ===")
    size = len(state.terraform_code)
    log_queue.put(make_log("AI", f"Generated {module_count} Terraform sections — {size:,} characters", "info"))
    log_queue.put(make_log("AI", "Terraform code generation complete ✔", "success"))
    return state
