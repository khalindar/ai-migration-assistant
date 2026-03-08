import queue
from models.platform_state import PlatformState
from utils.claude_client import complete
from utils.logger import make_log
from utils.json_parser import extract_json


SYSTEM = """You are a senior software architect. Analyze the provided repository structure and file contents.
Return a JSON object with these exact keys:
{
  "languages": ["list of programming languages detected"],
  "frameworks": ["list of frameworks/libraries detected"],
  "architecture_pattern": "monolith | microservices | serverless | MVC | event-driven | unknown",
  "services": ["list of distinct services or modules identified"],
  "databases": ["list of databases or data stores detected"],
  "message_queues": ["list of message queue technologies"],
  "api_gateways": ["list of API gateway or routing layers"],
  "entry_points": ["list of main entry point files"],
  "config_files": ["list of important config files found"],
  "has_docker": true or false,
  "has_kubernetes": true or false,
  "has_terraform": true or false,
  "has_ci_cd": true or false,
  "complexity": "low | medium | high",
  "summary": "2-3 sentence architectural summary"
}
Return only valid JSON, no markdown.
"""


def run(state: PlatformState, log_queue: queue.Queue) -> PlatformState:
    log_queue.put(make_log("AI", "Analyzing repository structure and patterns..."))
    log_queue.put(make_log("AI", "Detecting architecture patterns..."))

    file_tree = state.repo_structure.get("file_tree", {})
    directory_summary = state.repo_structure.get("directory_summary", "")
    key_files = file_tree.get("key_files", {})

    # Sample key files for the prompt (stay within token limits)
    sample_files = []
    total_chars = 0
    for path, content in key_files.items():
        chunk = content[:2000]
        sample_files.append(f"--- {path} ---\n{chunk}")
        total_chars += len(chunk)
        if total_chars > 40000:
            break

    files_text = "\n\n".join(sample_files)

    prompt = f"""Repository directory structure:
{directory_summary}

Key file contents (sampled):
{files_text}

Analyze this repository and return the JSON analysis."""

    log_queue.put(make_log("AI", "Sending repository data to Claude for analysis..."))
    raw = complete("repo_analysis_agent", SYSTEM, [{"role": "user", "content": prompt}], max_tokens=2048)

    analysis = extract_json(raw, fallback={})

    state.repo_analysis = analysis
    state.detected_languages = analysis.get("languages", [])
    state.detected_frameworks = analysis.get("frameworks", [])
    state.detected_services = analysis.get("services", [])
    state.architecture_pattern = analysis.get("architecture_pattern", "unknown")

    log_queue.put(make_log("AI", f"Architecture pattern: {state.architecture_pattern}", "info"))
    log_queue.put(make_log("AI", f"Languages detected: {', '.join(state.detected_languages)}", "info"))
    log_queue.put(make_log("AI", f"Services identified: {', '.join(state.detected_services)}", "info"))
    log_queue.put(make_log("AI", "Repository analysis complete ✔", "success"))
    return state
