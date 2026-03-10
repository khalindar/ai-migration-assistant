import queue as _queue
import streamlit as st
import streamlit.components.v1 as components
from models.platform_state import PlatformState, WORKFLOW_STEPS, StepStatus
from utils.logger import LogEvent, StepStatusEvent
from services.workflow_engine import get_engine, reset_engine
from ui.workflow_visualizer import (
    render_step_cards, render_progress_bar,
    render_artifact_content, render_inline_logs, ARTIFACT_LABELS,
    STATUS_CONFIG, MODEL_COLORS, _render_action_buttons, _step_outcome_summary,
)


def _try_get_store():
    try:
        from services.state_store import get_store
        return get_store()
    except Exception:
        return None


# ── Artifact modal — defined at module level so @st.dialog registers correctly ──
@st.dialog("📂 Artifact Viewer", width="large")
def _show_artifact_modal(state: PlatformState):
    step_id = st.session_state.get("active_artifact", "")
    label = ARTIFACT_LABELS.get(step_id, step_id.title())

    title_col, close_col = st.columns([5, 1])
    with title_col:
        st.markdown(
            f'<div style="color:#00d4ff;font-size:17px;font-weight:800;margin-bottom:4px;">'
            f'{label}</div>',
            unsafe_allow_html=True,
        )
    with close_col:
        if st.button("✕ Close", key="dialog_close_top", use_container_width=True, type="primary"):
            st.session_state.active_artifact = None
            st.rerun()

    st.divider()
    render_artifact_content(step_id, state)
    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("✕  Close", key="dialog_close_bottom", use_container_width=True):
        st.session_state.active_artifact = None
        st.rerun()


# ── Polling fragment — auto-reruns every 300ms without a full page rerun ──
# This eliminates page flicker: only the fragment's DOM area is updated each poll.
@st.fragment(run_every=0.3)
def _live_polling_fragment():
    engine = st.session_state.get("engine")
    state: PlatformState = st.session_state.get("platform_state")
    if not engine or not state:
        return

    step_logs = st.session_state.get("step_logs", {})

    # Drain queue unless a dialog is open
    if not st.session_state.get("active_artifact"):
        while not engine.log_queue.empty():
            try:
                event = engine.log_queue.get_nowait()
                if isinstance(event, StepStatusEvent):
                    state.step_statuses[event.step_id] = event.status
                elif isinstance(event, LogEvent):
                    sid = event.step_id or "system"
                    step_logs.setdefault(sid, []).append(event)
            except _queue.Empty:
                break
        st.session_state.step_logs = step_logs

    render_progress_bar(state)
    render_step_cards(state, step_logs, show_actions=True)

    # Trigger full page rerun when workflow completes → shows completion view
    if state.workflow_complete:
        st.rerun()


def render():
    if "platform_state" not in st.session_state:
        st.session_state.platform_state = PlatformState()
    if "step_logs" not in st.session_state:
        st.session_state.step_logs = {}
    if "engine" not in st.session_state:
        st.session_state.engine = get_engine()

    state: PlatformState = st.session_state.platform_state

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

    # ── Cache banner: shown when a saved analysis exists for this URL ──────
    if repo_url and repo_url.startswith("http"):
        store = _try_get_store()
        cached_meta = store.find_by_url(repo_url) if store else None
        dismissed = st.session_state.get("cache_dismissed_url", "") == repo_url

        if cached_meta and not dismissed:
            from services.state_store import format_saved_at
            saved_label = format_saved_at(cached_meta.get("saved_at", ""))
            provider = cached_meta.get("cloud_provider", "")
            steps_done = cached_meta.get("steps_completed", 0)
            provider_color = "#34a853" if provider == "GCP" else "#ff9900"

            st.markdown(
                f'<div style="background:linear-gradient(135deg,#0d2c1a,#0d1f2e);'
                f'border:1px solid #276749;border-left:4px solid #68d391;'
                f'border-radius:8px;padding:14px 16px;margin:12px 0;">'
                f'<div style="color:#68d391;font-weight:700;font-size:14px;margin-bottom:4px;">'
                f'📦 Saved Analysis Found</div>'
                f'<div style="color:#a0aec0;font-size:13px;">'
                f'Last saved <strong style="color:#e2e8f0;">{saved_label}</strong> &nbsp;·&nbsp; '
                f'<strong style="color:{provider_color};">{provider}</strong> &nbsp;·&nbsp; '
                f'{steps_done}/14 steps completed'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col_load, col_rerun = st.columns(2)
            with col_load:
                if st.button("📂  Load Saved Analysis", key="btn_load_cache",
                             use_container_width=True, type="primary"):
                    loaded = store.load(repo_url)
                    if loaded:
                        st.session_state.platform_state = loaded
                        st.session_state.selected_cloud_provider = loaded.cloud_provider
                        st.session_state.step_logs = {}
                        st.session_state.pop("active_artifact", None)
                        st.rerun()
            with col_rerun:
                if st.button("🔄  Re-run Fresh Analysis", key="btn_dismiss_cache",
                             use_container_width=True):
                    st.session_state.cache_dismissed_url = repo_url
                    st.rerun()

    safe_mode = st.checkbox(
        "Safe Mode — Simulate infrastructure (no real cloud resources created)",
        value=True,
    )

    # ── Cloud Provider Selection ────────────────────────────────
    st.markdown("""
    <div style="background:#1a1f2e;border:1px solid #2d3748;border-left:4px solid #00d4ff;
                border-radius:8px;padding:14px 16px;margin:20px 0 12px 0;">
        <div style="color:#00d4ff;font-weight:700;font-size:14px;margin-bottom:4px;">
            Target Cloud Provider
        </div>
        <div style="color:#a0aec0;font-size:13px;">
            Select the cloud platform to migrate this application to
        </div>
    </div>
    """, unsafe_allow_html=True)

    saved_provider = st.session_state.get("selected_cloud_provider", None)

    col_aws, col_gcp = st.columns(2)
    with col_aws:
        aws_selected = saved_provider == "AWS"
        aws_border = "border:2px solid #ff9900;" if aws_selected else "border:1px solid #30363d;"
        st.markdown(
            f'<div style="background:#161b22;{aws_border}border-radius:10px;padding:16px;text-align:center;">'
            f'<div style="font-size:28px;">☁️</div>'
            f'<div style="color:#ff9900;font-size:16px;font-weight:800;margin-top:6px;">AWS</div>'
            f'<div style="color:#718096;font-size:11px;margin-top:4px;">Amazon Web Services</div>'
            f'<div style="color:#a0aec0;font-size:11px;margin-top:6px;">EKS · RDS · ElastiCache · SQS</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Select AWS", key="btn_aws", use_container_width=True,
                     type="primary" if aws_selected else "secondary"):
            st.session_state.selected_cloud_provider = "AWS"
            st.rerun()

    with col_gcp:
        gcp_selected = saved_provider == "GCP"
        gcp_border = "border:2px solid #34a853;" if gcp_selected else "border:1px solid #30363d;"
        st.markdown(
            f'<div style="background:#161b22;{gcp_border}border-radius:10px;padding:16px;text-align:center;">'
            f'<div style="font-size:28px;">☁️</div>'
            f'<div style="color:#34a853;font-size:16px;font-weight:800;margin-top:6px;">GCP</div>'
            f'<div style="color:#718096;font-size:11px;margin-top:4px;">Google Cloud Platform</div>'
            f'<div style="color:#a0aec0;font-size:11px;margin-top:6px;">GKE · Cloud SQL · Memorystore · Pub/Sub</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Select GCP", key="btn_gcp", use_container_width=True,
                     type="primary" if gcp_selected else "secondary"):
            st.session_state.selected_cloud_provider = "GCP"
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    cloud_provider = saved_provider
    start_disabled = not repo_url or cloud_provider is None

    if st.button("🚀  Start Architecture Analysis", disabled=start_disabled,
                 use_container_width=True, type="primary"):
        engine = reset_engine()
        st.session_state.engine = engine
        st.session_state.step_logs = {}
        st.session_state.active_artifact = None

        state.repo_url = repo_url
        state.safe_mode = safe_mode
        state.cloud_provider = cloud_provider

        engine.start(state)
        st.rerun()

    if start_disabled and repo_url and not cloud_provider:
        st.caption("Please select a cloud provider above before starting.")

    _render_recent_sessions()


def _render_recent_sessions():
    """Show saved sessions below the input form."""
    store = _try_get_store()
    if not store:
        return
    sessions = store.list_sessions()
    if not sessions:
        return

    from services.state_store import format_saved_at

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#a0aec0;font-size:13px;font-weight:700;'
        'letter-spacing:0.08em;margin-bottom:10px;">RECENT SESSIONS</div>',
        unsafe_allow_html=True,
    )

    for session in sessions[:6]:
        provider = session.get("cloud_provider", "")
        provider_color = "#34a853" if provider == "GCP" else "#ff9900"
        saved_label = format_saved_at(session.get("saved_at", ""))
        steps_done = session.get("steps_completed", 0)
        complete = session.get("workflow_complete", False)
        status_icon = "✅" if complete else "⚡"
        repo_name = session.get("repo_name", session.get("repo_url", "").split("/")[-1])

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
                f'padding:10px 14px;">'
                f'<div style="display:flex;align-items:center;gap:8px;">'
                f'<span style="font-size:15px;">{status_icon}</span>'
                f'<span style="color:#e2e8f0;font-weight:700;font-size:13px;">{repo_name}</span>'
                f'<span style="color:{provider_color};font-size:12px;font-weight:600;'
                f'background:{provider_color}22;border-radius:4px;padding:1px 6px;">{provider}</span>'
                f'</div>'
                f'<div style="color:#4a5568;font-size:11px;margin-top:4px;">'
                f'{steps_done}/14 steps &nbsp;·&nbsp; {saved_label}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Load", key=f"load_session_{session['key']}",
                         use_container_width=True, type="secondary"):
                loaded = store.load(session["repo_url"])
                if loaded:
                    st.session_state.platform_state = loaded
                    st.session_state.selected_cloud_provider = loaded.cloud_provider
                    st.session_state.step_logs = {}
                    st.session_state.pop("active_artifact", None)
                    st.rerun()


def _render_completion_summary(state: PlatformState, step_logs: dict):
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0d2c1a,#0d1f3c);border:1px solid #276749;'
        'border-radius:12px;padding:16px 20px;margin-bottom:16px;text-align:center;">'
        '<div style="color:#68d391;font-size:18px;font-weight:800;">✅ Analysis Complete</div>'
        '<div style="color:#a0aec0;font-size:13px;margin-top:4px;">'
        'All steps completed — click any artifact button to explore results</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, step in enumerate(WORKFLOW_STEPS):
        sid = step["id"]
        status = state.step_statuses.get(sid, StepStatus.PENDING)
        cfg = STATUS_CONFIG[status]
        model = step.get("model", "Sonnet")
        model_color = MODEL_COLORS.get(model, "#00d4ff")
        outcome = _step_outcome_summary(sid, state) if status == StepStatus.COMPLETED else ""
        logs_for_step = step_logs.get(sid, [])
        log_count = len(logs_for_step)

        with cols[i % 2]:
            header = (
                f"{cfg['icon']} **#{i+1} {step['label']}**"
                + (f"  \n{outcome}" if outcome else "")
            )
            with st.expander(header, expanded=False):
                if status == StepStatus.COMPLETED and sid in ARTIFACT_LABELS:
                    _render_action_buttons(sid, state, idx=i)
                if logs_for_step:
                    render_inline_logs(logs_for_step)
                elif log_count == 0:
                    st.caption("No logs available.")


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
        if state.workflow_error:
            st.error(f"Workflow failed: {state.workflow_error}")
            render_step_cards(state, step_logs)
        else:
            _render_completion_summary(state, step_logs)

        st.markdown("<br/>", unsafe_allow_html=True)
        col_next, col_new = st.columns(2)
        with col_next:
            if st.button("🚀  View Deployment Simulation →", use_container_width=True, type="primary"):
                st.session_state.current_page = "Deployment"
                st.rerun()
        with col_new:
            if st.button("🔄  Run New Analysis", use_container_width=True):
                st.session_state.platform_state = PlatformState()
                st.session_state.step_logs = {}
                st.session_state.pop("selected_cloud_provider", None)
                st.session_state.active_artifact = None
                st.rerun()
        return

    # ── Live polling via fragment ─────────────────────────────
    # @st.fragment(run_every=0.3) auto-reruns every 300ms and only updates
    # its own DOM area — no full-page rerun, no flicker.
    _live_polling_fragment()
