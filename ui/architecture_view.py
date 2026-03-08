import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import networkx as nx
import math
from models.platform_state import PlatformState
from utils.diagram_generator import render_mermaid_html


def render():
    st.markdown("""
    <h2 style="color:#00d4ff;margin-bottom:4px;">Generated Infrastructure</h2>
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
        "Modernization Plan",
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
    st.markdown("#### Modernization Plan")
    plan = state.modernization_plan

    if not plan:
        st.caption("No modernization plan generated.")
        return

    # Current vs Target state
    col1, col2 = st.columns(2)
    with col1:
        current = plan.get("current_state", "—")
        st.markdown(
            f'<div style="background:#2d1b1b;border:1px solid #742a2a;border-radius:8px;padding:16px;min-height:120px;">'
            f'<div style="color:#fc8181;font-size:11px;font-weight:700;margin-bottom:8px;">CURRENT STATE</div>'
            f'<div style="color:#e2e8f0;font-size:13px;line-height:1.6;">{current}</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        target = plan.get("target_state", "—")
        st.markdown(
            f'<div style="background:#1c4532;border:1px solid #276749;border-radius:8px;padding:16px;min-height:120px;">'
            f'<div style="color:#68d391;font-size:11px;font-weight:700;margin-bottom:8px;">TARGET STATE</div>'
            f'<div style="color:#e2e8f0;font-size:13px;line-height:1.6;">{target}</div></div>',
            unsafe_allow_html=True,
        )

    # Recommendations
    st.markdown("##### Recommendations")
    for rec in plan.get("recommendations", []):
        priority_color = {"high": "#fc8181", "medium": "#f6ad55", "low": "#68d391"}.get(
            rec.get("priority", "medium"), "#a0aec0"
        )
        with st.expander(f"[{rec.get('priority','').upper()}] {rec.get('title','')}"):
            st.markdown(rec.get("description", ""))
            if rec.get("steps"):
                for step in rec["steps"]:
                    st.markdown(f"- {step}")

    # Migration phases
    if plan.get("migration_phases"):
        st.markdown("##### Migration Phases")
        phases = plan["migration_phases"]
        cols = st.columns(min(len(phases), 3))
        for i, phase in enumerate(phases[:3]):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div style="background:#1a1f2e;border:1px solid #2d3748;
                                border-top:3px solid #9f7aea;border-radius:8px;padding:14px;">
                        <div style="color:#9f7aea;font-size:11px;font-weight:700;">PHASE {phase.get('phase','')}</div>
                        <div style="color:#e2e8f0;font-size:14px;font-weight:700;margin:6px 0;">{phase.get('name','')}</div>
                        <div style="color:#718096;font-size:12px;">{phase.get('duration','')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Quick wins
    if plan.get("quick_wins"):
        st.markdown("##### Quick Wins")
        for win in plan["quick_wins"]:
            st.markdown(f"✅ {win}")
