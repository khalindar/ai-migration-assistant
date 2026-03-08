import json
import queue
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import networkx as nx
import math
from models.platform_state import PlatformState, StepStatus, WORKFLOW_STEPS
from utils.logger import LogEvent, StepStatusEvent, SOURCE_ICONS, LEVEL_COLORS
from utils.diagram_generator import render_mermaid_html

STATUS_CONFIG = {
    StepStatus.PENDING:   {"icon": "⏳", "color": "#4a5568", "bg": "#1a1f2e", "label": "Pending"},
    StepStatus.RUNNING:   {"icon": "⚡", "color": "#f6ad55", "bg": "#2d1f00", "label": "Running"},
    StepStatus.COMPLETED: {"icon": "✅", "color": "#68d391", "bg": "#1c4532", "label": "Complete"},
    StepStatus.FAILED:    {"icon": "❌", "color": "#fc8181", "bg": "#742a2a", "label": "Failed"},
}
MODEL_COLORS = {"Opus": "#9f7aea", "Sonnet": "#00d4ff"}

ARTIFACT_LABELS = {
    "summarize":      "Architecture Summary",
    "dependencies":   "Dependency Graph & Architecture Diagram",
    "infrastructure": "Infrastructure Plan",
    "modernization":  "Modernization Plan",
    "kubernetes":     "Kubernetes Manifests",
    "terraform":      "Terraform Code",
    "cost":           "Cost Estimation Breakdown",
}


# ─────────────────────────────────────────────────────────
# Action buttons — trigger artifact drawer via session state
# ─────────────────────────────────────────────────────────

def _render_action_buttons(step_id: str, state: PlatformState, idx: int):
    # Per-step config — computed lazily only for this step_id
    cfg = {
        "summarize": {
            "view_label": "🔍 View Summary",
            "has_data": bool(state.repo_summary),
            "dl_label": "⬇ Download .txt",
            "dl_file": "architecture_summary.txt",
            "dl_mime": "text/plain",
            "dl_fn": lambda: state.repo_summary or "",
        },
        "dependencies": {
            "view_label": "🗺 View Diagram & Graph",
            "has_data": bool(state.mermaid_diagram),
            "dl_label": "⬇ Download JSON",
            "dl_file": "dependency_graph.json",
            "dl_mime": "application/json",
            "dl_fn": lambda: json.dumps(state.service_dependencies, indent=2),
        },
        "infrastructure": {
            "view_label": "🏗 View Infra Plan",
            "has_data": bool(state.infrastructure_plan),
            "dl_label": "⬇ Download JSON",
            "dl_file": "infrastructure_plan.json",
            "dl_mime": "application/json",
            "dl_fn": lambda: json.dumps(state.infrastructure_plan, indent=2),
        },
        "modernization": {
            "view_label": "📋 View Modernization Plan",
            "has_data": bool(state.modernization_plan),
            "dl_label": "⬇ Download JSON",
            "dl_file": "modernization_plan.json",
            "dl_mime": "application/json",
            "dl_fn": lambda: json.dumps(state.modernization_plan, indent=2),
        },
        "kubernetes": {
            "view_label": "☸ View K8s Manifests",
            "has_data": bool(state.kubernetes_manifests.get("manifests")),
            "dl_label": "⬇ Download YAML",
            "dl_file": "k8s_manifests.yaml",
            "dl_mime": "text/plain",
            "dl_fn": lambda: "\n---\n".join(state.kubernetes_manifests.get("manifests", {}).values()),
        },
        "terraform": {
            "view_label": "🏛 View Terraform",
            "has_data": bool(state.terraform_code),
            "dl_label": "⬇ Download main.tf",
            "dl_file": "main.tf",
            "dl_mime": "text/plain",
            "dl_fn": lambda: state.terraform_code or "",
        },
        "cost": {
            "view_label": "💰 View Cost Breakdown",
            "has_data": bool(state.cost_estimation),
            "dl_label": "⬇ Download JSON",
            "dl_file": "cost_estimation.json",
            "dl_mime": "application/json",
            "dl_fn": lambda: json.dumps(state.cost_estimation, indent=2),
        },
    }

    if step_id not in cfg:
        return
    c = cfg[step_id]
    if not c["has_data"]:
        return

    active = st.session_state.get("active_artifact")
    is_viewing = active == step_id

    try:
        dl_data = c["dl_fn"]()
    except Exception:
        dl_data = ""

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "✕ Close" if is_viewing else c["view_label"],
            key=f"view_{step_id}_{idx}",
            use_container_width=True,
            type="primary" if is_viewing else "secondary",
        ):
            st.session_state.active_artifact = None if is_viewing else step_id
            st.rerun()
    with col2:
        st.download_button(
            c["dl_label"], data=dl_data, file_name=c["dl_file"], mime=c["dl_mime"],
            key=f"dl_{step_id}_{idx}", use_container_width=True,
        )


# ─────────────────────────────────────────────────────────
# Artifact drawer — full-width overlay rendered at top
# ─────────────────────────────────────────────────────────

def render_artifact_content(step_id: str, state: PlatformState):
    if step_id == "summarize":
        st.markdown(
            f'<div style="background:#0a1628;border-radius:8px;padding:20px;'
            f'line-height:1.7;color:#e2e8f0;font-size:14px;">{state.repo_summary}</div>',
            unsafe_allow_html=True,
        )

    elif step_id == "dependencies":
        t1, t2 = st.tabs(["🗺 Architecture Diagram", "🕸 Dependency Graph"])
        with t1:
            components.html(render_mermaid_html(state.mermaid_diagram), height=520, scrolling=True)
        with t2:
            _render_dep_graph_plotly(state)  # internal helper, stays private

    elif step_id == "infrastructure":
        resources = state.terraform_resources
        st.markdown(f'<div style="color:#a0aec0;font-size:13px;margin-bottom:12px;">'
                    f'{len(resources)} resources planned on <strong style="color:#00d4ff">'
                    f'{state.cloud_provider}</strong></div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, r in enumerate(resources):
            with cols[i % 3]:
                st.markdown(
                    f'<div style="background:#1a2040;border:1px solid #2d3a6b;border-radius:8px;'
                    f'padding:12px;margin-bottom:8px;">'
                    f'<div style="color:#00d4ff;font-size:11px;font-weight:700;">{r.get("type","")}</div>'
                    f'<div style="color:#e2e8f0;font-size:13px;font-weight:600;">{r.get("name","")}</div>'
                    f'<div style="color:#718096;font-size:11px;margin-top:4px;">{r.get("description","")}</div>'
                    f'</div>', unsafe_allow_html=True,
                )

    elif step_id == "modernization":
        plan = state.modernization_plan
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div style="color:#718096;font-size:11px;font-weight:700;margin-bottom:6px;">CURRENT STATE</div>', unsafe_allow_html=True)
            st.info(plan.get("current_state", "—"))
        with c2:
            st.markdown('<div style="color:#718096;font-size:11px;font-weight:700;margin-bottom:6px;">TARGET STATE</div>', unsafe_allow_html=True)
            st.success(plan.get("target_state", "—"))

        st.markdown('<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:16px 0 8px 0;">Recommendations</div>', unsafe_allow_html=True)
        for rec in plan.get("recommendations", []):
            p = rec.get("priority", "medium").upper()
            p_color = {"HIGH": "#fc8181", "MEDIUM": "#f6ad55", "LOW": "#68d391"}.get(p, "#a0aec0")
            with st.expander(f"[{p}] {rec.get('title','')}"):
                st.markdown(rec.get("description", ""))
                for s in rec.get("steps", []):
                    st.markdown(f"- {s}")

        if plan.get("quick_wins"):
            st.markdown('<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:16px 0 8px 0;">Quick Wins</div>', unsafe_allow_html=True)
            for w in plan["quick_wins"]:
                st.markdown(f'<div style="color:#68d391;font-size:13px;padding:4px 0;">✅ {w}</div>', unsafe_allow_html=True)

    elif step_id == "kubernetes":
        manifests = state.kubernetes_manifests.get("manifests", {})
        if manifests:
            sel = st.selectbox("Select manifest file", list(manifests.keys()), key="k8s_drawer_sel")
            st.code(manifests.get(sel, ""), language="yaml")

    elif step_id == "terraform":
        st.markdown(
            f'<div style="color:#a0aec0;font-size:13px;margin-bottom:12px;">'
            f'Provider: <strong style="color:#00d4ff">{state.cloud_provider}</strong> &nbsp;·&nbsp; '
            f'{len(state.terraform_resources)} resources &nbsp;·&nbsp; '
            f'{len(state.terraform_code):,} characters</div>',
            unsafe_allow_html=True,
        )
        st.code(state.terraform_code, language="hcl")

    elif step_id == "cost":
        import pandas as pd
        cost = state.cost_estimation
        total = cost.get("total_monthly", 0)
        annual = cost.get("total_annual", total * 12)
        m1, m2, m3 = st.columns(3)
        m1.metric("Monthly Cost", f"${total:,.2f}")
        m2.metric("Annual Cost", f"${annual:,.0f}")
        m3.metric("Cloud Provider", cost.get("provider", state.cloud_provider))
        items = cost.get("line_items", [])
        if items:
            df = pd.DataFrame([{
                "Resource": i.get("resource", ""),
                "Type": i.get("type", ""),
                "Monthly ($)": i.get("monthly_cost", 0),
            } for i in items])
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"Monthly ($)": st.column_config.NumberColumn(format="$%.2f")})
        tips = cost.get("savings_recommendations", [])
        if tips:
            st.markdown('<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:16px 0 8px 0;">Savings Recommendations</div>', unsafe_allow_html=True)
            for tip in tips:
                st.markdown(f'<div style="color:#f6ad55;font-size:13px;padding:4px 0;">💡 {tip}</div>', unsafe_allow_html=True)


def _render_dep_graph_plotly(state: PlatformState):
    graph_data = state.dependency_graph_data
    nodes = [n["id"] for n in graph_data.get("nodes", [])]
    edges = graph_data.get("edges", [])
    if not nodes:
        st.warning("No graph data.")
        return
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    for e in edges:
        G.add_edge(e["from"], e["to"])
    try:
        pos = nx.spring_layout(G, seed=42, k=2.0)
    except Exception:
        step = 2 * math.pi / max(len(nodes), 1)
        pos = {n: (math.cos(i * step), math.sin(i * step)) for i, n in enumerate(nodes)}
    ex, ey = [], []
    for e in edges:
        x0, y0 = pos.get(e["from"], (0, 0))
        x1, y1 = pos.get(e["to"], (0, 0))
        ex += [x0, x1, None]; ey += [y0, y1, None]
    fig = go.Figure(data=[
        go.Scatter(x=ex, y=ey, mode="lines",
                   line=dict(width=1.5, color="#4a5568"), hoverinfo="none"),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
                   mode="markers+text", text=nodes, textposition="top center",
                   textfont=dict(color="#e2e8f0", size=11),
                   marker=dict(size=22, color="#00d4ff", line=dict(color="#0080ff", width=2)),
                   hovertemplate="<b>%{text}</b><extra></extra>"),
    ])
    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        font=dict(color="#e2e8f0"), showlegend=False, height=420,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────
# Outcome summaries
# ─────────────────────────────────────────────────────────

def _step_outcome_summary(step_id: str, state: PlatformState) -> str:
    try:
        if step_id == "scan":
            fc = state.repo_structure.get("file_count", 0)
            dirs = len(state.repo_structure.get("file_tree", {}).get("directories", []))
            exts = list(state.repo_structure.get("extension_counts", {}).keys())[:4]
            return f"{fc} files · {dirs} dirs · {', '.join(exts)}"
        elif step_id == "analyze":
            return f"Pattern: {state.architecture_pattern} · {', '.join(state.detected_languages[:3])} · {len(state.detected_services)} services"
        elif step_id == "summarize":
            return (state.repo_summary[:160].replace("\n", " ") + "…") if state.repo_summary else "Summary generated"
        elif step_id == "dependencies":
            nodes = len(state.dependency_graph_data.get("nodes", []))
            edges = len(state.dependency_graph_data.get("edges", []))
            return f"{nodes} nodes · {edges} edges"
        elif step_id == "infrastructure":
            types = list({r.get("type") for r in state.terraform_resources})[:4]
            return f"{len(state.terraform_resources)} resources · {', '.join(types)}"
        elif step_id == "modernization":
            recs = len(state.modernization_plan.get("recommendations", []))
            return f"{recs} recommendations · {state.modernization_plan.get('estimated_timeline','TBD')}"
        elif step_id == "cloud":
            return f"Provider: {state.cloud_provider}"
        elif step_id == "kubernetes":
            return f"{len(state.kubernetes_manifests.get('manifests', {}))} manifests generated"
        elif step_id == "terraform":
            return f"{len(state.terraform_code):,} chars of HCL generated"
        elif step_id in ("bundle", "provision", "deploy", "validate"):
            return f"Endpoint: {state.simulated_endpoint or 'pending'}"
        elif step_id == "cost":
            total = state.cost_estimation.get("total_monthly", 0)
            return f"${total:,.2f}/month on {state.cloud_provider}"
    except Exception:
        pass
    return "Completed"


# ─────────────────────────────────────────────────────────
# Step cards
# ─────────────────────────────────────────────────────────

def render_step_cards(state: PlatformState, step_logs: dict = None, show_actions: bool = True):
    if step_logs is None:
        step_logs = {}

    for i, step in enumerate(WORKFLOW_STEPS):
        step_id = step["id"]
        label = step["label"]
        agent = step.get("agent", "")
        model = step.get("model", "Sonnet")
        status = state.step_statuses.get(step_id, StepStatus.PENDING)
        cfg = STATUS_CONFIG[status]
        model_color = MODEL_COLORS.get(model, "#00d4ff")

        is_active = st.session_state.get("active_artifact") == step_id
        active_border = f"box-shadow:0 0 0 2px #00d4ff;" if is_active else ""

        st.markdown(
            f'<div style="background:{cfg["bg"]};border:1px solid {cfg["color"]}55;'
            f'border-left:4px solid {cfg["color"]};border-radius:8px;'
            f'padding:12px 16px;margin-bottom:2px;{active_border}">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            # Left — icon + step label
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<span style="font-size:22px;">{cfg["icon"]}</span>'
            f'<div>'
            f'<div style="color:{cfg["color"]};font-size:11px;font-weight:700;letter-spacing:0.05em;">'
            f'{cfg["label"].upper()} &nbsp;·&nbsp;'
            f'<span style="color:{model_color};">STEP {i+1}</span></div>'
            f'<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin-top:1px;">{label}</div>'
            f'</div></div>'
            # Right — agent badge + model pill
            f'<div style="text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:4px;">'
            f'<div style="background:{model_color}22;border:1px solid {model_color}66;'
            f'border-radius:6px;padding:3px 10px;">'
            f'<span style="color:{model_color};font-size:12px;font-weight:800;">{agent}</span>'
            f'</div>'
            f'<div style="background:#1a1f2e;border:1px solid #2d3748;'
            f'border-radius:6px;padding:2px 8px;">'
            f'<span style="color:#a0aec0;font-size:11px;font-weight:600;">Claude {model}</span>'
            f'</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        logs_for_step = step_logs.get(step_id, [])

        if status == StepStatus.COMPLETED:
            if show_actions:
                _render_action_buttons(step_id, state, idx=i)

            outcome = _step_outcome_summary(step_id, state)
            with st.expander(f"📋 Logs — {outcome[:70]}", expanded=False):
                _render_inline_logs(logs_for_step)

        elif status == StepStatus.RUNNING and logs_for_step:
            with st.expander("⚡ Live logs (running...)", expanded=True):
                _render_inline_logs(logs_for_step)

        elif status == StepStatus.FAILED and logs_for_step:
            with st.expander("❌ Error logs", expanded=True):
                _render_inline_logs(logs_for_step)

        st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)


def _render_inline_logs(logs: list):
    if not logs:
        st.caption("No logs captured for this step.")
        return
    lines = []
    for log in logs[-30:]:
        icon = SOURCE_ICONS.get(log.source, "•")
        color = LEVEL_COLORS.get(log.level, "#a0aec0")
        lines.append(
            f'<div style="color:{color};font-size:11px;margin:2px 0;font-family:monospace;">'
            f'<span style="color:#4a5568;">[{log.timestamp}]</span> '
            f'<span style="color:#63b3ed;">[{icon} {log.source}]</span> '
            f'{log.message}</div>'
        )
    st.markdown(
        f'<div style="background:#0d1117;border-radius:6px;padding:10px;'
        f'max-height:200px;overflow-y:auto;">{"".join(lines)}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────
# Progress bar
# ─────────────────────────────────────────────────────────

def render_progress_bar(state: PlatformState):
    statuses = list(state.step_statuses.values())
    completed = sum(1 for s in statuses if s == StepStatus.COMPLETED)
    total = len(statuses)
    pct = int((completed / total) * 100) if total else 0
    st.markdown(
        f'<div style="margin:8px 0 16px 0;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
        f'<span style="color:#a0aec0;font-size:12px;">Workflow Progress</span>'
        f'<span style="color:#00d4ff;font-size:12px;font-weight:700;">{completed}/{total} steps — {pct}%</span>'
        f'</div>'
        f'<div style="background:#2d3748;border-radius:8px;height:8px;overflow:hidden;">'
        f'<div style="background:linear-gradient(90deg,#00d4ff,#0080ff);'
        f'width:{pct}%;height:100%;border-radius:8px;"></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────
# Queue drain
# ─────────────────────────────────────────────────────────

def drain_queue_and_refresh(engine, state: PlatformState, step_logs: dict,
                             step_placeholder, progress_placeholder) -> tuple[PlatformState, dict]:
    while not engine.log_queue.empty():
        try:
            event = engine.log_queue.get_nowait()
            if isinstance(event, StepStatusEvent):
                state.step_statuses[event.step_id] = event.status
            elif isinstance(event, LogEvent):
                sid = event.step_id or "system"
                step_logs.setdefault(sid, []).append(event)
        except queue.Empty:
            break

    with progress_placeholder.container():
        render_progress_bar(state)

    with step_placeholder.container():
        render_step_cards(state, step_logs, show_actions=True)

    return state, step_logs
