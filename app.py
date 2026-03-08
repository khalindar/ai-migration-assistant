import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="AI Platform Architect",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme global CSS
st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #0d1117; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0080ff, #00d4ff);
        color: #fff;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }
    .stButton > button[disabled] { background: #2d3748; color: #4a5568; }

    /* Inputs */
    .stTextInput > div > div > input {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        color: #e2e8f0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #718096; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background-color: #0080ff !important; color: #fff !important; }

    /* Expanders */
    .streamlit-expanderHeader { background-color: #161b22 !important; border-radius: 8px !important; }

    /* Chat */
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; }

    /* Metrics */
    [data-testid="stMetricValue"] { color: #00d4ff; }

    /* Selectbox */
    .stSelectbox > div > div { background-color: #161b22; border: 1px solid #30363d; }

    /* Checkbox */
    .stCheckbox { color: #e2e8f0; }

    /* Success/Info/Warning/Error */
    .stSuccess { background-color: #1c4532; border: 1px solid #276749; border-radius: 8px; }
    .stInfo { background-color: #1a2040; border: 1px solid #2d3a6b; border-radius: 8px; }

    /* Hide Streamlit branding but keep sidebar toggle visible */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: #0d1117; border-bottom: 1px solid #21262d; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* Top nav brand — injected via JS into parent header */
    #nav-brand-inject {
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        pointer-events: none;
        white-space: nowrap;
    }

    /* Sidebar radio nav */
    div[data-testid="stSidebar"] .stRadio > div {
        gap: 4px;
    }
    div[data-testid="stSidebar"] .stRadio label {
        background: transparent;
        border-radius: 8px;
        padding: 8px 12px;
        color: #a0aec0;
        font-size: 14px;
        font-weight: 500;
        width: 100%;
        cursor: pointer;
        transition: background 0.2s;
    }
    div[data-testid="stSidebar"] .stRadio label:hover {
        background: #21262d;
        color: #e2e8f0;
    }
    div[data-testid="stSidebar"] .stRadio [data-checked="true"] + div label,
    div[data-testid="stSidebar"] .stRadio input:checked ~ label {
        background: #0d2137;
        color: #00d4ff;
        border-left: 3px solid #00d4ff;
    }
    div[data-testid="stSidebar"] .stRadio [aria-checked="true"] {
        color: #00d4ff;
    }
    /* Hide radio circles */
    div[data-testid="stSidebar"] .stRadio input[type="radio"] { display: none; }
</style>
""", unsafe_allow_html=True)


# Inject brand title into the actual Streamlit header via JS
import streamlit.components.v1 as _components
_components.html("""
<script>
(function inject() {
    var doc = window.parent.document;
    if (doc.getElementById('nav-brand-inject')) return;
    var header = doc.querySelector('[data-testid="stHeader"]');
    if (!header) { setTimeout(inject, 200); return; }
    header.style.position = 'relative';
    var div = doc.createElement('div');
    div.id = 'nav-brand-inject';
    div.style.cssText = [
        'position:absolute',
        'left:50%',
        'top:50%',
        'transform:translate(-50%,-50%)',
        'text-align:center',
        'pointer-events:none',
        'white-space:nowrap',
        'line-height:1.25',
    ].join(';');
    div.innerHTML =
        '<div style="color:#00d4ff;font-size:24px;font-weight:800;letter-spacing:0.01em;">' +
        '&#127959;&#65039;&nbsp;&nbsp;AI Platform Architect</div>' +
        '<div style="color:#718096;font-size:12px;font-weight:400;letter-spacing:0.04em;">' +
        'Autonomous Cloud Architecture Discovery &amp; Deployment</div>';
    header.appendChild(div);
})();
</script>
""", height=0)

# Sidebar navigation
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 20px 0;text-align:center;border-bottom:1px solid #30363d;margin-bottom:16px;">
        <div style="font-size:28px;">🏗️</div>
        <div style="color:#00d4ff;font-weight:800;font-size:16px;margin-top:6px;">AI Platform Architect</div>
        <div style="color:#4a5568;font-size:11px;">v1.0 — Demo Edition</div>
    </div>
    """, unsafe_allow_html=True)

    page_options = [
        "🎯  Architecture Workflow",
        "🚀  Deployment Simulation",
        "💬  Architecture Q&A",
        "🏛️  Generated Infrastructure",
        "💰  Cost Estimation",
    ]
    page_keys = ["Dashboard", "Deployment", "Q&A", "Infrastructure", "Cost"]

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    current_index = page_keys.index(st.session_state.current_page)

    selected = st.radio(
        "Navigation",
        options=page_options,
        index=current_index,
        label_visibility="collapsed",
    )
    st.session_state.current_page = page_keys[page_options.index(selected)]

    # Status indicator
    state = st.session_state.get("platform_state")
    if state:
        st.markdown("<hr style='border-color:#30363d;margin:16px 0;'/>", unsafe_allow_html=True)
        if state.workflow_running:
            st.markdown('<div style="color:#f6ad55;font-size:14px;text-align:center;">⚡ Workflow Running...</div>', unsafe_allow_html=True)
        elif state.workflow_complete:
            st.markdown('<div style="color:#68d391;font-size:14px;text-align:center;">✅ Analysis Complete</div>', unsafe_allow_html=True)
            if state.repo_url:
                st.markdown(f'<div style="color:#4a5568;font-size:11px;text-align:center;word-break:break-all;">{state.repo_url.split("/")[-1]}</div>', unsafe_allow_html=True)


# Page routing
page = st.session_state.current_page

if page == "Dashboard":
    from ui.dashboard import render
    render()
elif page == "Deployment":
    from ui.deployment_view import render
    render()
elif page == "Q&A":
    from ui.qa_page import render
    render()
elif page == "Infrastructure":
    from ui.architecture_view import render
    render()
elif page == "Cost":
    from ui.cost_view import render
    render()
