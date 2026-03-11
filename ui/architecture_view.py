import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import networkx as nx
import math
from models.platform_state import PlatformState
from utils.diagram_generator import render_mermaid_html


def render():
    st.markdown("""
    <h2 style="color:#00d4ff;margin-bottom:4px;">Migration Blueprint</h2>
    <p style="color:#718096;margin-bottom:20px;">Architecture diagrams, service graph, and generated IaC artifacts</p>
    """, unsafe_allow_html=True)

    state: PlatformState = st.session_state.get("platform_state", PlatformState())

    if not state.workflow_complete:
        st.info("Run the architecture workflow on the Dashboard page first.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Architecture Diagram",
        "Dependency Graph",
        "Kubernetes YAML",
        "Terraform Code",
        "Migration Plan",
    ])

    with tab1:
        _render_mermaid(state)

    with tab2:
        _render_dependency_graph(state)

    with tab3:
        _render_kubernetes(state)

    with tab4:
        _render_terraform(state)

    with tab5:
        _render_modernization(state)


def _render_mermaid(state: PlatformState):
    st.markdown("#### Architecture Diagram")
    if not state.mermaid_diagram:
        st.caption("No diagram generated.")
        return

    components.html(render_mermaid_html(state.mermaid_diagram), height=500, scrolling=True)

    with st.expander("View Mermaid Source"):
        st.code(state.mermaid_diagram, language="text")


def _render_dependency_graph(state: PlatformState):
    st.markdown("#### Service Dependency Graph")
    graph_data = state.dependency_graph_data

    if not graph_data or not graph_data.get("nodes"):
        st.caption("No dependency graph data available.")
        return

    nodes = [n["id"] for n in graph_data["nodes"]]
    edges = graph_data["edges"]

    # Build networkx graph for layout
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    for e in edges:
        G.add_edge(e["from"], e["to"])

    try:
        pos = nx.spring_layout(G, seed=42, k=2.0)
    except Exception:
        angle_step = 2 * math.pi / max(len(nodes), 1)
        pos = {n: (math.cos(i * angle_step), math.sin(i * angle_step)) for i, n in enumerate(nodes)}

    # Edge traces
    edge_x, edge_y = [], []
    for e in edges:
        x0, y0 = pos.get(e["from"], (0, 0))
        x1, y1 = pos.get(e["to"], (0, 0))
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1.5, color="#4a5568"),
        hoverinfo="none",
    )

    # Node traces
    node_x = [pos[n][0] for n in nodes]
    node_y = [pos[n][1] for n in nodes]

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=nodes,
        textposition="top center",
        textfont=dict(color="#e2e8f0", size=11),
        marker=dict(
            size=20,
            color="#00d4ff",
            line=dict(color="#0080ff", width=2),
            opacity=0.9,
        ),
        hovertemplate="<b>%{text}</b><extra></extra>",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        paper_bgcolor="#161b22",
        plot_bgcolor="#0d1117",
        font=dict(color="#e2e8f0"),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(t=20, b=20, l=20, r=20),
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_kubernetes(state: PlatformState):
    st.markdown("#### Kubernetes Manifests")
    k8s = state.kubernetes_manifests

    if not k8s:
        st.caption("No Kubernetes manifests generated.")
        return

    namespace = k8s.get("namespace", "app-production")
    services = k8s.get("services", [])

    st.markdown(
        f'<div style="color:#68d391;font-size:13px;margin-bottom:12px;">'
        f'Namespace: <strong>{namespace}</strong> | Services: <strong>{len(services)}</strong></div>',
        unsafe_allow_html=True,
    )

    manifests = k8s.get("manifests", {})
    if manifests:
        selected = st.selectbox("Select manifest", list(manifests.keys()))
        content = manifests.get(selected, "")
        st.code(content, language="yaml")
        st.download_button(
            f"Download {selected}.yaml",
            data=content,
            file_name=f"{selected}.yaml",
            mime="text/plain",
        )
    else:
        st.caption("No manifest content available.")


def _render_terraform(state: PlatformState):
    st.markdown("#### Terraform Code")

    if not state.terraform_code:
        st.caption("No Terraform code generated.")
        return

    st.markdown(
        f'<div style="color:#f6ad55;font-size:13px;margin-bottom:12px;">'
        f'Provider: <strong>{state.cloud_provider}</strong> | '
        f'Resources: <strong>{len(state.terraform_resources)}</strong></div>',
        unsafe_allow_html=True,
    )

    st.code(state.terraform_code, language="hcl")
    st.download_button(
        "Download main.tf",
        data=state.terraform_code,
        file_name="main.tf",
        mime="text/plain",
    )


def _render_modernization(state: PlatformState):
    import re as _re
    st.markdown("#### Migration Plan")
    plan = state.modernization_plan

    if not plan:
        st.caption("No Migration Plan generated.")
        return

    def _to_bullets(text: str) -> list:
        parts = _re.split(r'\.\s+(?=[A-Z])|[\n\r]+', text.strip())
        return [p.strip().rstrip('.') for p in parts if p.strip()]

    current_bullets = _to_bullets(plan.get("current_state", "—"))
    target_bullets  = _to_bullets(plan.get("target_state", "—"))

    cur_rows = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #3d2020;">'
        f'<span style="color:#fc8181;flex-shrink:0;margin-top:2px;">●</span>'
        f'<span style="color:#e2e8f0;font-size:13px;line-height:1.5;">{b}</span></div>'
        for b in current_bullets
    )
    tgt_rows = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #1e4030;">'
        f'<span style="color:#68d391;flex-shrink:0;margin-top:2px;">●</span>'
        f'<span style="color:#e2e8f0;font-size:13px;line-height:1.5;">{b}</span></div>'
        for b in target_bullets
    )

    col1, col2 = st.columns(2)
    with col1:
        st.html(
            f'<div style="background:#2d1b1b;border:1px solid #742a2a;border-radius:10px;padding:16px;height:100%;">'
            f'<div style="color:#fc8181;font-size:11px;font-weight:700;letter-spacing:0.08em;margin-bottom:10px;">⚠ CURRENT STATE</div>'
            f'{cur_rows}</div>'
        )
    with col2:
        st.html(
            f'<div style="background:#1c4532;border:1px solid #276749;border-radius:10px;padding:16px;height:100%;">'
            f'<div style="color:#68d391;font-size:11px;font-weight:700;letter-spacing:0.08em;margin-bottom:10px;">✅ TARGET STATE</div>'
            f'{tgt_rows}</div>'
        )

    # Migration roadmap
    phases = plan.get("migration_phases", [])
    if phases:
        st.markdown(
            '<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:20px 0 10px 0;">Migration Roadmap</div>',
            unsafe_allow_html=True,
        )
        phase_cols = st.columns(len(phases[:4]))
        for j, phase in enumerate(phases[:4]):
            acts_html = "".join(
                f'<div style="color:#a0aec0;font-size:11px;padding:3px 0;border-bottom:1px solid #2d3748;">▸ {a}</div>'
                for a in phase.get("activities", [])
            )
            with phase_cols[j]:
                st.html(
                    f'<div style="background:#1a1f2e;border:1px solid #2d3748;border-top:3px solid #9f7aea;'
                    f'border-radius:8px;padding:14px;">'
                    f'<div style="color:#9f7aea;font-size:10px;font-weight:700;letter-spacing:0.06em;">PHASE {phase.get("phase","")}</div>'
                    f'<div style="color:#e2e8f0;font-size:13px;font-weight:700;margin:4px 0;">{phase.get("name","")}</div>'
                    f'<div style="color:#f6ad55;font-size:11px;margin-bottom:8px;">⏱ {phase.get("duration","")}</div>'
                    f'{acts_html}</div>'
                )

    # Recommendations
    st.markdown(
        '<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:20px 0 8px 0;">Recommendations</div>',
        unsafe_allow_html=True,
    )
    for rec in plan.get("recommendations", []):
        p = rec.get("priority", "medium").upper()
        with st.expander(f"[{p}] {rec.get('title','')}"):
            st.markdown(rec.get("description", ""))
            for step in rec.get("steps", []):
                st.markdown(f"- {step}")

    # Quick wins
    if plan.get("quick_wins"):
        st.markdown(
            '<div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:16px 0 8px 0;">Quick Wins</div>',
            unsafe_allow_html=True,
        )
        for win in plan["quick_wins"]:
            st.markdown(f'<div style="color:#68d391;font-size:13px;padding:4px 0;">✅ {win}</div>', unsafe_allow_html=True)
