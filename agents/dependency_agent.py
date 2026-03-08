import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.diagram_generator import build_mermaid, build_plotly_graph_data
from utils.json_parser import extract_json


SYSTEM = """You are a software architect mapping service dependencies.
Analyze the repository and return a JSON dependency map.
Format:
{
  "dependencies": {
    "ServiceA": ["ServiceB", "Database1"],
    "ServiceB": ["Redis", "ServiceC"],
    "User": ["APIGateway"],
    "APIGateway": ["ServiceA", "ServiceB"]
  },
  "external_services": ["list of external services like AWS S3, Stripe, Twilio"],
  "data_stores": ["list of databases and caches"],
  "entry_point": "the top-level service users interact with"
}
Use short, clean service names (PascalCase, no spaces). Return only valid JSON."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Building service dependency graph..."))
    log_queue.put(make_log("AI", "Identifying microservices and data flows..."))

    analysis = state.repo_analysis
    prompt = f"""Repository analysis:
- Architecture pattern: {analysis.get('architecture_pattern')}
- Services: {analysis.get('services')}
- Databases: {analysis.get('databases')}
- Message queues: {analysis.get('message_queues')}
- API gateways: {analysis.get('api_gateways')}
- Frameworks: {analysis.get('frameworks')}

Directory structure:
{state.repo_structure.get('directory_summary', '')}

Map all service dependencies and return JSON."""

    raw = complete("dependency_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=2048)

    data = extract_json(raw, fallback={"dependencies": {}})

    dependencies = data.get("dependencies", {})
    state.service_dependencies = data

    # Build diagram artifacts
    state.mermaid_diagram = build_mermaid(dependencies)
    state.dependency_graph_data = build_plotly_graph_data(dependencies)

    node_count = len(state.dependency_graph_data.get("nodes", []))
    edge_count = len(state.dependency_graph_data.get("edges", []))

    log_queue.put(make_log("AI", f"Dependency graph built: {node_count} nodes, {edge_count} edges", "info"))
    log_queue.put(make_log("AI", "Mermaid architecture diagram generated ✔", "success"))
    return state
