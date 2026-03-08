import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log


SYSTEM = """You are a senior cloud architect creating an executive-level architecture summary.
Based on the repository analysis, write a clear, structured summary suitable for a Senior Leadership audience.
Format the output as Markdown bullet points grouped under these 4 short bold headings:
**What it does**, **Architecture**, **Key Components**, **Cloud Readiness**.
Each heading should have 2-4 concise bullet points. Be insightful and specific, not generic."""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Generating architecture summary..."))

    analysis = state.repo_analysis
    prompt = f"""Repository analysis results:
- Languages: {', '.join(analysis.get('languages', []))}
- Frameworks: {', '.join(analysis.get('frameworks', []))}
- Architecture pattern: {analysis.get('architecture_pattern', 'unknown')}
- Services: {', '.join(analysis.get('services', []))}
- Databases: {', '.join(analysis.get('databases', []))}
- Message queues: {', '.join(analysis.get('message_queues', []))}
- Has Docker: {analysis.get('has_docker', False)}
- Has Kubernetes: {analysis.get('has_kubernetes', False)}
- Has Terraform: {analysis.get('has_terraform', False)}
- Has CI/CD: {analysis.get('has_ci_cd', False)}
- Complexity: {analysis.get('complexity', 'medium')}
- Summary: {analysis.get('summary', '')}

Write a comprehensive architecture summary for this repository."""

    log_queue.put(make_log("AI", "Synthesizing architecture insights..."))
    summary = complete("repo_summary_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=1024)

    state.repo_summary = summary.strip()
    log_queue.put(make_log("AI", "Architecture summary generated ✔", "success"))
    return state
