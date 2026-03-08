import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="AI Cloud Migration Assistant",
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
    .st-emotion-cache-k39vsp { font-size: 14px !important; }

    /* Remove top gap above first heading inside dialog artifact content */
    div[role="dialog"] h1:first-child,
    div[role="dialog"] h2:first-child,
    div[role="dialog"] h3:first-child,
    div[role="dialog"] .stMarkdown:first-child h1,
    div[role="dialog"] .stMarkdown:first-child h2,
    div[role="dialog"] .stMarkdown:first-child h3 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* Reduce excessive top padding, ensure bottom has enough room */
    [data-testid="stMainBlockContainer"] {
        padding-top: 2rem !important;
        padding-bottom: 6rem !important;
    }

    /* Primary buttons — blue gradient */
    .stButton > button[data-testid="baseButton-primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #0080ff, #00d4ff) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton > button[data-testid="baseButton-primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover { opacity: 0.85; }

    /* Secondary buttons — subtle dark style */
    .stButton > button[data-testid="baseButton-secondary"],
    .stButton > button[data-testid="stBaseButton-secondary"] {
        background: #1a1f2e !important;
        border: 1px solid #30363d !important;
        color: #a0aec0 !important;
        border-radius: 8px;
        font-weight: 500;
        transition: background 0.2s, color 0.2s;
    }
    .stButton > button[data-testid="baseButton-secondary"]:hover,
    .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background: #21262d !important;
        color: #e2e8f0 !important;
        border-color: #4a5568 !important;
    }

    /* Download buttons — subtle, not green */
    .stDownloadButton > button {
        background: #1a1f2e !important;
        border: 1px solid #30363d !important;
        color: #a0aec0 !important;
        border-radius: 8px;
        font-weight: 500;
    }
    .stDownloadButton > button:hover {
        background: #21262d !important;
        color: #e2e8f0 !important;
    }

    .stButton > button[disabled] { background: #2d3748 !important; color: #4a5568 !important; border: none !important; }

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

    /* Expanders — default */
    .streamlit-expanderHeader { background-color: #161b22 !important; border-radius: 8px !important; }

    /* Expanders — highlight open/selected card in completion summary */
    details[open] > summary,
    details[open] > summary:hover {
        background: linear-gradient(135deg, #0d2137, #0a1628) !important;
        border-left: 3px solid #00d4ff !important;
        border-radius: 8px 8px 0 0 !important;
        color: #00d4ff !important;
        box-shadow: 0 0 0 1px #00d4ff44 !important;
    }
    details[open] {
        border: 1px solid #00d4ff44 !important;
        border-radius: 8px !important;
    }

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

    /* Hide native Streamlit dialog X button — it can't clear our session state,
       so it causes the dialog to immediately reopen on the next rerun.
       We provide our own Close button inside the dialog instead. */
    [data-testid="stModal"] button[aria-label="Close"],
    [data-testid="stDialog"] button[aria-label="Close"],
    div[role="dialog"] button[aria-label="Close"] { display: none !important; }

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
        '&#127959;&#65039;&nbsp;&nbsp;AI Cloud Migration Assistant</div>' +
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
        <div style="color:#00d4ff;font-weight:800;font-size:16px;margin-top:6px;">Navigation :</div>
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
