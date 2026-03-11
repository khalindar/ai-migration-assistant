import json
import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a principal cloud architect. Analyze the application and produce a modernization plan.
You MUST always return a non-empty plan with at least 3 recommendations and 3 migration phases, even for simple apps.
Return only this JSON structure with no markdown fences:
{
  "current_state": "one paragraph describing the current architecture",
  "target_state": "one paragraph describing the ideal cloud-native target architecture",
  "recommendations": [
    {"title": "short title", "priority": "high", "effort": "medium", "impact": "high", "description": "2-3 sentences", "steps": ["step 1", "step 2", "step 3"]}
  ],
  "migration_phases": [
    {"phase": 1, "name": "Foundation", "duration": "4-6 weeks", "activities": ["activity 1", "activity 2"]}
  ],
  "risks": [
    {"risk": "risk description", "mitigation": "mitigation strategy"}
  ],
  "quick_wins": ["quick win 1", "quick win 2", "quick win 3"],
  "estimated_timeline": "X-Y months"
}"""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating modernization plan using Claude Opus..."))
    log_queue.put(make_log("AI", "Analyzing current architecture against cloud-native best practices..."))

    analysis = state.repo_analysis

    prompt = f"""Analyze this application and generate a complete modernization plan.

Current application facts:
- Architecture pattern: {analysis.get('architecture_pattern', 'unknown')}
- Languages: {', '.join(analysis.get('languages', []))}
- Frameworks: {', '.join(analysis.get('frameworks', []))}
- Services: {', '.join(analysis.get('services', []))}
- Databases: {', '.join(analysis.get('databases', []))}
- Message queues: {', '.join(analysis.get('message_queues', []))}
- Has Docker: {analysis.get('has_docker', False)}
- Has Kubernetes: {analysis.get('has_kubernetes', False)}
- Has CI/CD: {analysis.get('has_ci_cd', False)}
- Complexity: {analysis.get('complexity', 'medium')}
- Target cloud: {state.cloud_provider}

Service dependencies: {json.dumps(state.service_dependencies.get('dependencies', {}), indent=2)[:1000]}

Architecture summary: {state.repo_summary[:800]}

Generate a comprehensive modernization plan with realistic recommendations for migrating this to cloud-native {state.cloud_provider}.
Even if the app is already partially cloud-ready, identify improvements for reliability, scalability, security, and cost optimisation.
Return only valid JSON, no markdown."""

    log_queue.put(make_log("AI", "Claude Opus reasoning through modernization strategy..."))
    raw = complete("modernization_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=8096)

    data = extract_json(raw, fallback={})

    # Ensure we always have content
    if not data.get("recommendations"):
        data["recommendations"] = [
            {
                "title": "Containerize All Services",
                "priority": "high", "effort": "medium", "impact": "high",
                "description": "Package all services in Docker containers for consistent deployment.",
                "steps": ["Write Dockerfiles", "Build and test images", "Push to container registry"]
            },
            {
                "title": "Implement CI/CD Pipeline",
                "priority": "high", "effort": "medium", "impact": "high",
                "description": "Automate build, test, and deploy using GitHub Actions.",
                "steps": ["Create pipeline config", "Add automated tests", "Configure deployment stages"]
            },
            {
                "title": "Adopt Infrastructure as Code",
                "priority": "medium", "effort": "medium", "impact": "high",
                "description": "Use Terraform to manage all cloud resources declaratively.",
                "steps": ["Define Terraform modules", "Set up remote state", "Automate provisioning"]
            },
        ]
    if not data.get("migration_phases"):
        data["migration_phases"] = [
            {"phase": 1, "name": "Foundation", "duration": "4-6 weeks",
             "activities": ["Containerize services", "Set up CI/CD", "Configure cloud accounts"]},
            {"phase": 2, "name": "Migration", "duration": "6-8 weeks",
             "activities": ["Deploy to Kubernetes", "Migrate databases", "Configure networking"]},
            {"phase": 3, "name": "Optimisation", "duration": "4-6 weeks",
             "activities": ["Performance tuning", "Cost optimisation", "Security hardening"]},
        ]
    if not data.get("current_state"):
        data["current_state"] = analysis.get("summary", "Current architecture requires modernization assessment.")
    if not data.get("target_state"):
        data["target_state"] = f"Cloud-native {state.cloud_provider} deployment with Kubernetes, managed databases, automated CI/CD, and full observability."
    if not data.get("estimated_timeline"):
        data["estimated_timeline"] = "3-6 months"
    if not data.get("quick_wins"):
        data["quick_wins"] = ["Add health check endpoints", "Enable structured logging", "Set up cloud cost alerts"]

    state.modernization_plan = data
    rec_count = len(data.get("recommendations", []))
    phase_count = len(data.get("migration_phases", []))

    log_queue.put(make_log("AI", f"Generated {rec_count} recommendations · {phase_count} migration phases", "info"))
    log_queue.put(make_log("AI", f"Timeline: {data.get('estimated_timeline', 'TBD')}", "info"))
    log_queue.put(make_log("AI", "Migration Plan complete ✔", "success"))
    return state
