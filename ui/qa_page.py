import streamlit as st
import streamlit.components.v1 as components
from models.platform_state import PlatformState
import agents.architecture_qa_agent as qa_agent


EXAMPLE_QUESTIONS = [
    "What are the key services in this application?",
    "What database does the payment service depend on?",
    "What services depend on the authentication service?",
    "What happens if the API gateway goes down?",
    "What are the top modernization recommendations?",
    "What would this cost on an annual basis?",
    "How many Kubernetes pods will be running?",
    "What are the main security risks identified?",
]


def render():
    st.markdown("""
    <h2 style="color:#00d4ff;margin-bottom:4px;">Architecture Q&A</h2>
    <p style="color:#718096;margin-bottom:20px;">
        Ask questions about the analyzed architecture — powered by Claude Opus with tool-use
    </p>
    """, unsafe_allow_html=True)

    state: PlatformState = st.session_state.get("platform_state", PlatformState())

    if not state.workflow_complete:
        st.info("Run the architecture workflow on the Dashboard page first.")
        return

    # Initialize conversation history
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []
    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = []

    # Example questions
    st.markdown("**Example questions:**")
    cols = st.columns(4)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        with cols[i % 4]:
            if st.button(q, key=f"eq_{i}", use_container_width=True):
                st.session_state.pending_question = q

    st.markdown("<hr style='border-color:#30363d;margin:16px 0;'/>", unsafe_allow_html=True)

    # Render conversation
    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tools_used"):
                tools_str = ", ".join([f"`{t}`" for t in msg["tools_used"]])
                st.caption(f"Tools consulted: {tools_str}")

    # Handle pending question from example button
    pending = st.session_state.pop("pending_question", None)

    # Chat input
    user_input = st.chat_input("Ask anything about the architecture...")
    question = pending or user_input

    if question:
        # Display user message
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.qa_messages.append({"role": "user", "content": question})

        # Get answer
        with st.chat_message("assistant"):
            with st.spinner("Claude Opus is analyzing the architecture..."):
                answer, updated_history, tools_used = qa_agent.ask(
                    question,
                    state,
                    st.session_state.qa_history,
                )
            st.markdown(answer)
            if tools_used:
                tools_str = ", ".join([f"`{t}`" for t in tools_used])
                st.caption(f"Tools consulted: {tools_str}")

        st.session_state.qa_history = updated_history
        st.session_state.qa_messages.append({
            "role": "assistant",
            "content": answer,
            "tools_used": tools_used,
        })
        # Scroll to top so user reads the answer from the beginning
        components.html(
            "<script>window.parent.document.querySelector('.main').scrollTo({top:0,behavior:'smooth'});</script>",
            height=0,
        )

    # Clear conversation
    if st.session_state.qa_messages:
        if st.button("Clear Conversation", key="clear_qa"):
            st.session_state.qa_history = []
            st.session_state.qa_messages = []
            st.rerun()
