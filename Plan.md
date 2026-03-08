# AI Platform Architect — Implementation Plan

## Overview

An AI-powered internal developer platform that analyzes a GitHub repository and automatically designs, modernizes, and simulates deployment of a cloud architecture. Built for VP-level demos.

---

## Selected Approach

### Approach 1 — Background Thread + Queue (Primary pipeline)
All 14 workflow steps run in a daemon background thread. Agents write `LogEvent` / `StepStatusEvent` objects to a `queue.Queue`. The Streamlit UI polls every 300ms, drains the queue, and re-renders progress. This gives live, real-time step-by-step visibility without blocking the UI thread.

### Approach 3 — Claude Agent SDK with Tool-Use (Q&A page only)
The Architecture Q&A page (Page 3) uses Claude Opus with 7 registered tools (`get_service_list`, `get_dependency_graph`, `get_infrastructure_plan`, `get_modernization_plan`, `get_kubernetes_manifests`, `get_terraform_code`, `get_cost_estimation`). The agent autonomously decides which tools to call before answering.

---

## Architecture

```
app.py (Streamlit entry point)
├── ui/dashboard.py          — Input form + live pipeline step cards
├── ui/deployment_view.py    — Terminal output + simulated pod status
├── ui/qa_page.py            — Chat with Claude Opus (7 tools)
├── ui/architecture_view.py  — Mermaid diagrams + K8s/TF code viewer
├── ui/cost_view.py          — Monthly cost breakdown + Plotly charts
└── ui/workflow_visualizer.py — Step card renderer + artifact drawer

services/
├── workflow_engine.py       — Background thread orchestrator, _StepQueue
├── repo_cloner.py           — GitPython shallow clone + file tree builder
└── terraform_executor.py   — Docker/Terraform/K8s simulators (Safe Mode)

agents/ (14-step pipeline)
├── repo_scanner_agent.py
├── repo_analysis_agent.py
├── repo_summary_agent.py
├── dependency_agent.py
├── infrastructure_agent.py
├── modernization_agent.py   — Claude Opus
├── cloud_selection_agent.py — Logic-based (LUMI → GCP, else AWS)
├── kubernetes_agent.py
├── terraform_agent.py
├── deployment_agent.py      — Steps 10-13 (bundle/provision/deploy/validate)
├── cost_estimation_agent.py
└── architecture_qa_agent.py — Page 3 Opus with tool-use

models/platform_state.py    — PlatformState (single shared Pydantic model)
utils/
├── claude_client.py         — Anthropic SDK wrapper (Opus vs Sonnet routing)
├── json_parser.py           — 4-strategy robust JSON extractor
├── logger.py                — LogEvent, StepStatusEvent, _StepQueue
└── diagram_generator.py    — Mermaid HTML renderer for components.html
```

---

## 14-Step Agent Pipeline

| Step | ID | Agent | Model | Output |
|------|----|-------|-------|--------|
| 1 | scan | RepoScannerAgent | Sonnet | repo_structure |
| 2 | analyze | RepoAnalysisAgent | Sonnet | repo_analysis, detected_services |
| 3 | summarize | RepoSummaryAgent | Sonnet | repo_summary |
| 4 | dependencies | DependencyAgent | Sonnet | service_dependencies, mermaid_diagram |
| 5 | infrastructure | InfrastructureAgent | Sonnet | infrastructure_plan, terraform_resources |
| 6 | modernization | ModernizationAgent | **Opus** | modernization_plan |
| 7 | cloud | CloudSelectionAgent | Logic | cloud_provider (AWS or GCP) |
| 8 | kubernetes | KubernetesAgent | Sonnet | kubernetes_manifests |
| 9 | terraform | TerraformAgent | Sonnet | terraform_code (raw HCL) |
| 10 | bundle | DeploymentAgent | Executor | Docker build simulation |
| 11 | provision | DeploymentAgent | Executor | Terraform apply simulation |
| 12 | deploy | DeploymentAgent | Executor | K8s deploy simulation |
| 13 | validate | DeploymentAgent | Executor | Health check simulation |
| 14 | cost | CostEstimationAgent | Sonnet | cost_estimation |

---

## Key Design Decisions

### State Management
- Single `PlatformState` Pydantic model in `st.session_state` — no files, no APIs between agents
- All agents receive and return the same state object

### Live Log Streaming
- `_StepQueue` wrapper auto-tags each `LogEvent` with `step_id`
- UI drains queue every 300ms and routes logs to per-step buckets in `step_logs` dict
- `show_actions=True` in both polling and completed states — View buttons appear immediately when a step completes, not at end of full workflow

### Artifact Viewing (VP-level UX)
- View buttons use `@st.dialog(width="large")` defined at module level in `dashboard.py`
- Dialog opens as a true modal popup overlay on button click (sets `active_artifact` + `st.rerun()`)
- Dialog is triggered for both `workflow_running` and `workflow_complete` states
- Modal includes native Streamlit X button (top-right) + internal "✕ Close" button
- Dialog calls `render_artifact_content(step_id, state)` from `workflow_visualizer.py`
- Close button inside dialog clears `active_artifact` + reruns

### Duplicate Key Prevention
- Initial pre-loop render removed — only `drain_queue_and_refresh` renders step cards during polling
- `st.empty()` placeholder replaced each iteration (no accumulation)
- Widget keys are scoped per step (`view_{step_id}_{idx}`, `dl_{step_id}_{idx}`) — unique within each render pass

### JSON Parsing
- `utils/json_parser.py` with 4 fallback strategies: direct parse → strip markdown fences → brace-depth walk → sanitize trailing commas
- Applied to all 7 JSON-returning agents

### Cloud Selection
- User answers LUMI dependency question (radio, horizontal)
- LUMI dependency → GCP (with 5 GCP-specific justifications)
- No LUMI → AWS (with 5 AWS-specific justifications)
- Recommendation card shows instantly on radio selection

### Token Limits
- Modernization, Kubernetes, Terraform agents use `max_tokens=8096`
- TerraformAgent returns raw HCL directly (not JSON-wrapped) to avoid parsing failures
- ModernizationAgent has guaranteed fallback content when Claude returns empty arrays

---

## UI Pages

| Page | Sidebar Label | File |
|------|--------------|------|
| 1 | 🎯 Architecture Workflow | `ui/dashboard.py` |
| 2 | 🚀 Deployment Simulation | `ui/deployment_view.py` |
| 3 | 💬 Architecture Q&A | `ui/qa_page.py` |
| 4 | 🏛️ Generated Infrastructure | `ui/architecture_view.py` |
| 5 | 💰 Cost Estimation | `ui/cost_view.py` |

---

## UI/UX Improvements Implemented

### Navigation
- Sidebar uses `st.radio` (not buttons) to preserve state during workflow polling reruns
- App title "🏗️ AI Platform Architect" injected into Streamlit header via JavaScript `window.parent.document`
- Title: 20px bold cyan; Caption: 11px muted grey, horizontally centered

### Step Cards
- Agent name displayed in colored pill badge (Opus = purple `#9f7aea`, Sonnet = cyan `#00d4ff`)
- Model name in separate dark pill (`Claude Sonnet` / `Claude Opus`)
- Active artifact step gets cyan glow ring (`box-shadow`)
- Step outcome summary shown in log expander header

### Artifact Modals
- `@st.dialog(width="large")` defined in `dashboard.py` (avoids imported-module registration issues)
- True modal overlay with native Streamlit X button + internal "✕ Close" button
- Per-artifact content: Summary (text), Dependencies (tabs: Diagram + Plotly graph), Infrastructure (3-col resource cards), Modernization (current/target + expandable recs), Kubernetes (manifest selector + code), Terraform (HCL code block), Cost (metrics + dataframe + savings tips)

### Q&A Page
- Scroll-to-top JS injected after each answer so user reads from the beginning
- Example questions grid (4 columns)

### Dashboard
- Scroll-to-top JS on "Start Analysis" click
- Context bar (3 columns): Repository name, Cloud Provider, Execution Mode

---

## Setup

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
streamlit run app.py   # http://localhost:8501
```
