# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

```bash
# Create and activate virtual environment
uv venv .venv --python 3.11
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Set API key
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

# Run the app
streamlit run app.py
# Opens at http://localhost:8501
```

There are no automated tests, linting, or build scripts in this project.

## Architecture Overview

This is a **Streamlit app** that analyzes a GitHub repository and generates a cloud migration/modernization plan using a multi-agent Claude pipeline.

### Core Flow

1. User submits a GitHub URL on the Dashboard
2. `WorkflowEngine` (background daemon thread) runs a **14-step agent pipeline** sequentially
3. Agents write logs to a `queue.Queue`; the UI polls every 300ms to re-render progress
4. All state lives in `PlatformState` (Pydantic model) stored in `st.session_state`

### Agent Pipeline (14 Steps)

| Steps | Agent | Model | Output |
|-------|-------|-------|--------|
| 1 | RepoScannerAgent | Sonnet | repo_structure |
| 2 | RepoAnalysisAgent | Sonnet | repo_analysis, detected_services |
| 3 | RepoSummaryAgent | Sonnet | repo_summary |
| 4 | DependencyAgent | Sonnet | service_dependencies, mermaid_diagram |
| 5 | InfrastructureAgent | Sonnet | infrastructure_plan |
| 6 | ModernizationAgent | **Opus** | modernization_plan |
| 7 | CloudSelectionAgent | Logic | cloud_provider (AWS or GCP) |
| 8 | KubernetesAgent | Sonnet | kubernetes_manifests |
| 9 | TerraformAgent | Sonnet | terraform_code |
| 10-13 | DeploymentAgent | Executor | Docker/Terraform/K8s (simulated) |
| 14 | CostEstimationAgent | Sonnet | cost_estimation |

**Cloud selection:** User picks AWS or GCP via visual cards before starting. `CloudSelectionAgent` (Step 7) is a pass-through that confirms the pre-set provider.

### Key Files

- `app.py` — Entry point; 5-page routing, dark theme CSS, sidebar nav
- `models/platform_state.py` — `PlatformState` (single source of truth) + `WORKFLOW_STEPS` config
- `services/workflow_engine.py` — Background thread orchestrator; `_StepQueue` tags logs with `step_id`
- `services/repo_cloner.py` — GitPython shallow clone (`--depth=1`) + file tree builder
- `services/terraform_executor.py` — `TerraformExecutor`, `DockerExecutor`, `KubernetesExecutor` (Safe Mode = simulation)
- `utils/claude_client.py` — Anthropic SDK wrapper; routes Opus vs Sonnet calls
- `utils/json_parser.py` — Robust JSON extraction with 4 fallback strategies
- `agents/architecture_qa_agent.py` — Page 3 chat; uses Agent SDK with 7 tools

### UI Pages

| Page | File | Purpose |
|------|------|---------|
| Dashboard | `ui/dashboard.py` | Input form + live pipeline step cards |
| Deployment | `ui/deployment_view.py` | Terminal output + pod status |
| Q&A | `ui/qa_page.py` | Chat with Opus (7 tools) |
| Infrastructure | `ui/architecture_view.py` | Mermaid diagrams + K8s/TF code |
| Cost | `ui/cost_view.py` | Monthly cost breakdown + Plotly charts |

### Design Decisions

- **No persistence:** All state is in-memory (Streamlit `session_state`) — ephemeral per session
- **Safe Mode on by default:** Prevents accidental cloud resource creation; simulators add realistic delays
- **Opus used sparingly:** Only for modernization (Step 6) and Q&A chat to balance cost/quality
- **Model routing:** `utils/claude_client.py` selects Sonnet vs Opus per agent
- **Pydantic everywhere:** `PlatformState`, `LogEvent`, `StepStatusEvent` are all typed models
