import streamlit as st
from models.platform_state import PlatformState


def render():
    st.markdown("""
    <h2 style="color:#00d4ff;margin-bottom:4px;">Deployment Simulation</h2>
    <p style="color:#718096;margin-bottom:20px;">Infrastructure provisioning and Kubernetes deployment output</p>
    """, unsafe_allow_html=True)

    state: PlatformState = st.session_state.get("platform_state", PlatformState())

    if not state.workflow_complete:
        st.info("Run the architecture workflow on the Dashboard page first.")
        return

    dep = state.deployment_status

    # Endpoint banner
    endpoint = state.simulated_endpoint
    if endpoint:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#0d4f3c,#1a6b52);
                        border:1px solid #68d391;border-radius:12px;padding:20px;margin-bottom:20px;text-align:center;">
                <div style="color:#68d391;font-size:12px;font-weight:700;letter-spacing:0.1em;">APPLICATION ENDPOINT</div>
                <div style="color:#fff;font-size:18px;font-weight:700;margin:8px 0;">{endpoint}</div>
                <div style="color:#9ae6b4;font-size:12px;">Status: <strong>LIVE ✔</strong> (Simulated)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Infrastructure Provisioning")
        tf_results = dep.get("terraform", {})
        _render_resource_table(tf_results, "Terraform")

    with col2:
        st.markdown("#### Container Images Built")
        docker_results = dep.get("docker", {})
        _render_resource_table(docker_results, "Docker")

    st.markdown("#### Kubernetes Pods")
    k8s_results = dep.get("kubernetes", {})
    _render_pod_table(k8s_results)

    # Deployment summary metrics
    st.markdown("#### Deployment Summary")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        _metric_card("Resources Provisioned", str(len(tf_results)), "#00d4ff")
    with m2:
        _metric_card("Images Built", str(len(docker_results)), "#68d391")
    with m3:
        _metric_card("Pods Running", str(len(k8s_results)), "#9f7aea")
    with m4:
        mode = "Simulated" if state.safe_mode else "Live"
        _metric_card("Deployment Mode", mode, "#f6ad55")


def _render_resource_table(results: dict, source: str):
    if not results:
        st.caption("No results yet.")
        return

    rows = []
    for name, status in results.items():
        icon = "✅" if status in ("created", "running", f"{name}:latest") else "⚙️"
        rows.append(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    background:#1a1f2e;border-radius:6px;padding:8px 12px;margin:4px 0;
                    border-left:3px solid #00d4ff;">
            <span style="color:#e2e8f0;font-size:13px;">{name}</span>
            <span style="color:#68d391;font-size:12px;">{icon} {status}</span>
        </div>
        """)

    st.markdown("".join(rows), unsafe_allow_html=True)


def _render_pod_table(k8s_results: dict):
    if not k8s_results:
        st.caption("No pods deployed.")
        return

    col = "display:grid;grid-template-columns:2fr 1fr 1fr 1fr;"
    header = (
        f'<div style="{col}background:#0d1117;border-radius:8px 8px 0 0;padding:8px 12px;border-bottom:1px solid #30363d;">'
        '<span style="color:#718096;font-size:11px;font-weight:700;">SERVICE</span>'
        '<span style="color:#718096;font-size:11px;font-weight:700;">STATUS</span>'
        '<span style="color:#718096;font-size:11px;font-weight:700;">READY</span>'
        '<span style="color:#718096;font-size:11px;font-weight:700;">RESTARTS</span>'
        '</div>'
    )

    rows = []
    for svc, status in k8s_results.items():
        rows.append(
            f'<div style="{col}background:#161b22;padding:8px 12px;border-bottom:1px solid #21262d;">'
            f'<span style="color:#e2e8f0;font-size:13px;">{svc}</span>'
            '<span style="color:#68d391;font-size:12px;">Running ✔</span>'
            '<span style="color:#68d391;font-size:12px;">1/1</span>'
            '<span style="color:#a0aec0;font-size:12px;">0</span>'
            '</div>'
        )

    st.html(
        f'<div style="border:1px solid #30363d;border-radius:8px;overflow:hidden;">'
        f'{header}{"".join(rows)}</div>'
    )


def _metric_card(label: str, value: str, color: str):
    st.markdown(
        f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px;text-align:center;border-top:3px solid {color};">
            <div style="color:{color};font-size:24px;font-weight:800;">{value}</div>
            <div style="color:#718096;font-size:11px;margin-top:4px;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
