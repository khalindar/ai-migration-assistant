# Agentic Cloud Migration Assistant — Implementation Plan

## Overview

An AI-powered internal developer platform that analyzes a GitHub repository and automatically designs, modernizes, and simulates deployment of a cloud architecture. Built for Senior leadership-level demos.

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
├── cloud_selection_agent.py — Pass-through: confirms user-selected provider (AWS or GCP)
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
- Polling uses `@st.fragment(run_every=0.3)` — fragment auto-reruns every 300ms and only updates its own DOM section (no full-page rerun, no flicker). When workflow completes, `st.rerun()` inside the fragment triggers a full page rerun to show the completion view
- Steps 11-13 (provision/deploy/validate) remain in RUNNING state throughout the workflow — simulates ongoing cloud infrastructure activity during demos; only bundle (step 10) transitions to COMPLETED

### Artifact Viewing (Leadership level UX)
- View buttons use `@st.dialog(width="large")` defined at module level in `dashboard.py`
- Dialog opens as a true modal popup overlay on button click (sets `active_artifact` + `st.rerun()`)
- Dialog is triggered for both `workflow_running` and `workflow_complete` states
- Native Streamlit X button is **hidden via CSS** — it cannot clear `active_artifact` from session state, causing the dialog to immediately reopen on the next polling rerun
- Dialog has "✕ Close" buttons at both **top and bottom**; clicking either clears `active_artifact` + reruns
- Polling is **paused while dialog is open** (`active_artifact` is set) — prevents any automatic rerun from reopening the dialog
- Dialog calls `render_artifact_content(step_id, state)` from `workflow_visualizer.py`

### Duplicate Key Prevention
- Initial pre-loop render removed — only `drain_queue_and_refresh` renders step cards during polling
- `st.empty()` placeholder replaced each iteration (no accumulation)
- Widget keys are scoped per step (`view_{step_id}_{idx}`, `dl_{step_id}_{idx}`) — unique within each render pass

### JSON Parsing
- `utils/json_parser.py` with 4 fallback strategies: direct parse → strip markdown fences → brace-depth walk → sanitize trailing commas
- Applied to all 7 JSON-returning agents

### Cloud Selection
- User selects AWS or GCP via two visual cards on the input panel before starting the workflow
- Selected card highlights with a colored border; button changes to `type="primary"`
- `state.cloud_provider` set directly from the card selection before workflow starts
- `cloud_selection_agent` (Step 7) is a pass-through that confirms the pre-set provider in logs

### Cost Consistency
- `total_monthly` metric and the line-item subtotal always match: both are derived by summing `line_items[].monthly_cost` — Claude's `total_monthly` field is ignored to avoid discrepancies between the header metric and the table subtotal
- `total_annual` falls back to `total_monthly * 12` if not returned by the agent

### Provider-Aware Agent Prompts
- All agents that reference cloud services use explicit AWS vs GCP service names in their SYSTEM prompts so Claude generates provider-correct output for both clouds
- `InfrastructureAgent`: SYSTEM prompt lists AWS (EKS, RDS, ElastiCache, ALB, SQS, S3) and GCP (GKE, Cloud SQL, Memorystore, Cloud Load Balancing, Pub/Sub, Cloud Storage) resources; provider-correct fallback resources used if JSON extraction fails
- `KubernetesAgent`: SYSTEM prompt instructs Claude to use only standard Kubernetes resources (no cloud-specific CRDs/annotations) to keep embedded YAML JSON-safe; per-service fallback Deployments generated if parsing fails
- `CostEstimationAgent`: SYSTEM prompt lists both AWS and GCP service names; `_fallback_cost(provider)` returns provider-correct line items (GCP: GKE, Cloud SQL, Memorystore; AWS: EKS, RDS, ElastiCache)
- `CostEstimationAgent`: resource dict access uses `.get()` to avoid `KeyError` on malformed resource dicts

### JSON Parser
- `utils/json_parser.py` uses 4 strategies: direct parse → strip markdown fences → brace-depth walk → sanitize trailing commas
- `_sanitize` does NOT strip `//` or `/* */` comments — these patterns appear inside YAML strings and URLs embedded in JSON values and stripping them corrupts valid content

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
| 4 | 🏛️ Migration Blueprint | `ui/architecture_view.py` |
| 5 | 💰 Cost Estimation | `ui/cost_view.py` |

---

## UI/UX Improvements Implemented

### Navigation
- Sidebar uses `st.radio` (not buttons) to preserve state during workflow polling reruns
- App title injected into Streamlit header via JavaScript `window.parent.document`
- Top padding `2rem`, bottom padding `6rem` via `stMainBlockContainer` CSS override — ensures buttons at the bottom of the page are always visible
- Primary buttons: blue gradient; secondary buttons + download buttons: subtle dark `#1a1f2e` style — targeted via both `baseButton-*` and `stBaseButton-*` data-testid variants (Streamlit naming varies by version)
- Completion view: compact 2-column step grid where each step card is a clickable `st.expander` — clicking reveals logs and View/Download artifact buttons inline (no separate log box); header shows step icon, number, label, and outcome summary; "🚀 View Deployment Simulation →" navigation at bottom
- Architecture summary formatted as Markdown bullet points (4 sections: What it does, Architecture, Key Components, Cloud Readiness) — prompt updated in `repo_summary_agent.py`; `render_artifact_content` uses `st.markdown()` to render bullets

### Step Cards
- Agent name displayed in colored pill badge (Opus = purple `#9f7aea`, Sonnet = cyan `#00d4ff`)
- Model name in separate dark pill (`Claude Sonnet` / `Claude Opus`)
- Active artifact step gets cyan glow ring (`box-shadow`)
- Step outcome summary shown in log expander header

### HTML Rendering
- Use `st.html()` (not `st.markdown(..., unsafe_allow_html=True)`) for multi-row HTML tables — Markdown treats lines with 4+ leading spaces as code blocks, which causes raw HTML to appear as text instead of rendering
- `st.markdown` is fine for single-block HTML snippets with no indented child elements

### Artifact Modals
- `@st.dialog(width="large")` defined in `dashboard.py` (avoids imported-module registration issues)
- True modal overlay with native Streamlit X button + internal "✕ Close" button
- Per-artifact content: Summary (text), Dependencies (tabs: Diagram + Plotly graph), Infrastructure (3-col resource cards), Modernization (see below), Kubernetes (manifest selector + code), Terraform (HCL code block), Cost (metrics + dataframe + savings tips)
- Modernization view is identical in both the artifact modal (`workflow_visualizer.py`) and the Migration Blueprint page (`architecture_view.py`): bullet-pointed Current State (red ●) vs Target State (green ●) side-by-side panels, Migration Roadmap phase cards with activities, expandable Recommendations, Quick Wins list

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
