import time
import streamlit as st
import streamlit.components.v1 as components
from models.platform_state import PlatformState, WORKFLOW_STEPS, StepStatus
from services.workflow_engine import get_engine, reset_engine
from ui.workflow_visualizer import (
    render_step_cards, render_progress_bar, drain_queue_and_refresh,
    render_artifact_content, ARTIFACT_LABELS,
)

CLOUD_RECOMMENDATIONS = {
    True: {
        "provider": "GCP",
        "color": "#34a853",
        "icon": "☁️",
        "headline": "Google Cloud Platform — Strongly Recommended",
        "reasons": [
            "LUMI integration requires native GCP service connectivity (VPC peering, Shared VPC)",
            "GKE (Google Kubernetes Engine) provides seamless workload identity for LUMI service accounts",
            "Cloud SQL and Memorystore are co-located with LUMI's data residency requirements",
            "Anthos Service Mesh enables zero-trust communication between your app and LUMI endpoints",
            "Lower egress cost when traffic stays within the same Google Cloud backbone",
        ],
        "caution": None,
    },
    False: {
        "provider": "AWS",
        "color": "#ff9900",
        "icon": "☁️",
        "headline": "Amazon Web Services — Strongly Recommended",
        "reasons": [
            "AWS has the broadest managed service portfolio — EKS, RDS, ElastiCache, SQS all production-proven",
            "Largest global region footprint gives lowest latency for most enterprise deployments",
            "AWS Organizations + IAM provides enterprise-grade multi-account governance out of the box",
            "Cost tooling (Cost Explorer, Savings Plans) gives strongest FinOps control",
            "No LUMI dependency means no GCP-specific networking requirements to satisfy",
        ],
        "caution": "If LUMI dependency is added later, cross-cloud networking will require VPN or Interconnect.",
    },
}


# ── Artifact modal — defined at module level so @st.dialog registers correctly ──
@st.dialog("📂 Artifact Viewer", width="large")
def _show_artifact_modal(state: PlatformState):
    step_id = st.session_state.get("active_artifact", "")
    label = ARTIFACT_LABELS.get(step_id, step_id.title())

    st.markdown(
        f'<div style="color:#00d4ff;font-size:17px;font-weight:800;margin-bottom:16px;">'
        f'{label}</div>',
        unsafe_allow_html=True,
    )

    render_artifact_content(step_id, state)

    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("✕  Close", use_container_width=True):
        st.session_state.active_artifact = None
        st.rerun()


def render():
    if "platform_state" not in st.session_state:
        st.session_state.platform_state = PlatformState()
    if "step_logs" not in st.session_state:
        st.session_state.step_logs = {}
    if "engine" not in st.session_state:
        st.session_state.engine = get_engine()

    state: PlatformState = st.session_state.platform_state

    # Open artifact modal if requested (works on both complete and polling states)
    if st.session_state.get("active_artifact") and (state.workflow_running or state.workflow_complete):
        _show_artifact_modal(state)

    if not state.workflow_running and not state.workflow_complete:
        _render_input_panel(state)
    else:
        _render_workflow_panel(state)


def _render_input_panel(state: PlatformState):
    st.markdown("""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                padding:24px;margin-bottom:20px;">
        <h3 style="color:#e2e8f0;margin:0 0 4px 0;">Repository Configuration</h3>
        <p style="color:#718096;font-size:13px;margin:0;">
            Enter a public GitHub repository URL to begin AI-powered architecture analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository",
    )

    safe_mode = st.checkbox(
        "Safe Mode — Simulate infrastructure (no real cloud resources created)",
        value=True,
    )

    # ── LUMI Question ──────────────────────────────────────────
    st.markdown("""
    <div style="background:#1a1f2e;border:1px solid #2d3748;border-left:4px solid #f6ad55;
                border-radius:8px;padding:14px 16px;margin:20px 0 8px 0;">
        <div style="color:#f6ad55;font-weight:700;font-size:14px;margin-bottom:4px;">
            Cloud Provider Selection
        </div>
        <div style="color:#a0aec0;font-size:13px;">
            Does this application have any dependency with
            <strong style="color:#fff;">LUMI</strong>
            or any internal services that require GCP?
        </div>
    </div>
    """, unsafe_allow_html=True)

    lumi_choice = st.radio(
        "LUMI dependency",
        options=["Yes — this app depends on LUMI / GCP services",
                 "No — this app has no LUMI or GCP dependencies"],
        index=None,
        label_visibility="collapsed",
        horizontal=True,
    )

    lumi_dep = None
    if lumi_choice is not None:
        lumi_dep = lumi_choice.startswith("Yes")
        st.session_state.lumi_dependency = lumi_dep

    if lumi_dep is None:
        lumi_dep = st.session_state.get("lumi_dependency", None)

    # ── Recommendation card ────────────────────────────────────
    if lumi_dep is not None:
        rec = CLOUD_RECOMMENDATIONS[lumi_dep]
        color = rec["color"]
        st.markdown(
            f'<div style="border-left:4px solid {color};background:#0d1a0d;'
            f'border-radius:8px;padding:14px 18px;margin:12px 0;">'
            f'<span style="color:{color};font-weight:800;font-size:15px;">'
            f'{rec["icon"]} {rec["headline"]}</span></div>',
            unsafe_allow_html=True,
        )
        for reason in rec["reasons"]:
            st.markdown(
                f'<div style="color:#b7d9b7;font-size:13px;padding:3px 0 3px 18px;">'
                f'✓ &nbsp;{reason}</div>',
                unsafe_allow_html=True,
            )
        if rec.get("caution"):
            st.warning(f"⚠ {rec['caution']}")

    st.markdown("<br/>", unsafe_allow_html=True)

    start_disabled = not repo_url or lumi_dep is None
    if st.button("🚀  Start Architecture Analysis", disabled=start_disabled,
                 use_container_width=True, type="primary"):
        engine = reset_engine()
        st.session_state.engine = engine
        st.session_state.step_logs = {}
        st.session_state.active_artifact = None

        state.repo_url = repo_url
        state.safe_mode = safe_mode
        state.lumi_dependency = lumi_dep
        state.cloud_provider = "GCP" if lumi_dep else "AWS"

        engine.start(state)
        # Scroll to top so user sees workflow from step 1
        components.html(
            "<script>window.parent.document.querySelector('.main').scrollTo({top:0,behavior:'smooth'});</script>",
            height=0,
        )
        st.rerun()

    if start_disabled and repo_url:
        st.caption("Please answer the LUMI question above before starting.")


def _render_workflow_panel(state: PlatformState):
    engine = st.session_state.get("engine")
    step_logs = st.session_state.step_logs

    # ── Context bar ────────────────────────────────────────────
    provider_color = "#34a853" if state.cloud_provider == "GCP" else "#ff9900"
    mode_color = "#f6ad55" if state.safe_mode else "#fc8181"
    mode_label = "SAFE MODE" if state.safe_mode else "LIVE MODE"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'padding:12px;text-align:center;margin-bottom:12px;">'
            f'<div style="color:#718096;font-size:11px;letter-spacing:0.05em;">REPOSITORY</div>'
            f'<div style="color:#e2e8f0;font-size:13px;font-weight:700;">'
            f'{state.repo_url.split("/")[-1]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'padding:12px;text-align:center;margin-bottom:12px;">'
            f'<div style="color:#718096;font-size:11px;letter-spacing:0.05em;">CLOUD PROVIDER</div>'
            f'<div style="color:{provider_color};font-size:18px;font-weight:800;">'
            f'{state.cloud_provider}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'padding:12px;text-align:center;margin-bottom:12px;">'
            f'<div style="color:#718096;font-size:11px;letter-spacing:0.05em;">EXECUTION MODE</div>'
            f'<div style="color:{mode_color};font-size:14px;font-weight:700;">'
            f'{mode_label}</div></div>',
            unsafe_allow_html=True,
        )

    # ── Workflow complete ───────────────────────────────────────
    if state.workflow_complete:
        render_progress_bar(state)
        render_step_cards(state, step_logs)

        if state.workflow_error:
            st.error(f"Workflow failed: {state.workflow_error}")
        else:
            st.success(
                "✅ Analysis complete — click View on any step to explore the generated artifacts. "
                "Use the sidebar to navigate all pages."
            )

        if st.button("🔄  Run New Analysis", use_container_width=True):
            st.session_state.platform_state = PlatformState()
            st.session_state.step_logs = {}
            st.session_state.pop("lumi_dependency", None)
            st.session_state.active_artifact = None
            st.rerun()
        return

    # ── Live polling ─────────────────────────────────────────
    # Single placeholder — only drain_queue_and_refresh writes here, no pre-render
    progress_placeholder = st.empty()
    step_placeholder = st.empty()

    if state.workflow_running:
        while state.workflow_running or (engine and not engine.log_queue.empty()):
            state, step_logs = drain_queue_and_refresh(
                engine, state, step_logs, step_placeholder, progress_placeholder,
            )
            st.session_state.step_logs = step_logs
            time.sleep(0.3)
            if not state.workflow_running and engine.log_queue.empty():
                break

        # Final drain then rerun → enters workflow_complete branch above
        state, step_logs = drain_queue_and_refresh(
            engine, state, step_logs, step_placeholder, progress_placeholder,
        )
        st.session_state.step_logs = step_logs
        st.rerun()
