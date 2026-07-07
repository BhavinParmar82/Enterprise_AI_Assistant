import asyncio
import html
import streamlit as st

from orchestrator.EnterpriseGraph import EnterpriseGraph

# ==========================================================
# Page Configuration
# ==========================================================

st.set_page_config(
    page_title="Enterprise AI Assistant",
    page_icon="🤖",
    layout="wide"
)

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        font-family: 'Inter', sans-serif;
    }

    body {
        background: radial-gradient(circle at top left, #1f3b5a 0%, #0a1523 45%, #03111d 100%);
    }

    .reportview-container .main .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        padding-bottom: 2rem;
        background: transparent;
    }

    .stApp {
        background: transparent;
    }

    .css-18e3th9 {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 20px 70px rgba(0, 0, 0, 0.23);
        border-radius: 24px;
    }

    .stButton>button {
        background: linear-gradient(135deg, #2d9fff 0%, #6b53ff 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 1rem;
        box-shadow: 0 16px 38px -16px rgba(45, 159, 255, 0.7);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 22px 42px -18px rgba(45, 159, 255, 0.85);
    }

    .stMarkdown p,
    .stMarkdown li,
    .stMarkdown h1,
    .stMarkdown h2,
    .stMarkdown h3 {
        color: #e8f1ff;
    }

    .stChatMessage {
        border-radius: 20px;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .stChatMessage div[class*="message"] {
        background: transparent !important;
    }

    .css-1d391kg,
    .css-1outpf7 {
        background: rgba(5, 19, 34, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .stSidebar .css-18e3th9 {
        background: rgba(7, 24, 43, 0.96) !important;
    }

    .hero-card {
        background: linear-gradient(180deg, rgba(10, 28, 54, 0.95), rgba(20, 34, 62, 0.80));
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 24px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.20);
        backdrop-filter: blur(16px);
    }

    .hero-card h1 {
        margin: 0;
        font-size: 1.8rem;
        letter-spacing: -0.04em;
        color: #ffffff;
    }

    .hero-card p {
        margin: 0.45rem 0 0;
        color: #cbd8ff;
        font-size: 0.96rem;
        line-height: 1.5;
    }

    .status-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 22px;
        padding: 1rem;
        margin-bottom: 1rem;
        min-height: 135px;
        color: #e8f1ff;
    }

    .status-card h3 {
        margin-bottom: 0.35rem;
        color: #ffffff;
    }

    .status-card p {
        margin: 0;
        color: #cbd8ff;
        line-height: 1.7;
        white-space: pre-wrap;
    }

    .footer-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 20px;
        padding: 1rem 1.2rem;
        margin-top: 1.5rem;
        color: #d7e2ff;
    }

    .footer-card p {
        margin: 0.4rem 0;
        color: #c4d0ff;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 999px;
        color: #e8f1ff;
        padding: 0.45rem 0.9rem;
        font-size: 0.95rem;
    }

    .css-1q8dd3e.edgvbvh3 {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# Session State
# ==========================================================

# Chat bubbles shown in the UI (plain dicts, for rendering only).
if "messages" not in st.session_state:
    st.session_state.messages = []

# Real graph state history (HumanMessage/AIMessage objects) — this is
# what actually gets fed back into the graph so context isn't lost
# between turns.
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# One EnterpriseGraph instance for the whole session, so the MCP
# connection and compiled graph are only built once.
if "enterprise_graph" not in st.session_state:
    st.session_state.enterprise_graph = EnterpriseGraph()
    st.session_state.mcp_ready = False

# One persistent event loop for the whole session. Calling asyncio.run()
# on every rerun would open/close a new loop each time, which breaks
# any long-lived async resources (like the MCP client's connections)
# opened on a previous loop.
if "event_loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    st.session_state.event_loop = loop

if "planner_status" not in st.session_state:
    st.session_state.planner_status = "Waiting for user query..."

if "execution_status" not in st.session_state:
    st.session_state.execution_status = "No execution yet."


def run_async(coro):
    """Run a coroutine on this session's persistent event loop."""
    return st.session_state.event_loop.run_until_complete(coro)


# --------------------------------------------------
# Eager initialization — runs once, right when the app first opens.
# EnterpriseGraph.initialize() itself is idempotent (it checks
# self.graph is None), so even though run_query() also calls it on
# every turn, that later call is just a no-op check, not a rebuild.
# --------------------------------------------------

if not st.session_state.mcp_ready:
    with st.spinner("Connecting to MCP servers and loading tools..."):
        try:
            run_async(st.session_state.enterprise_graph.initialize())
            st.session_state.mcp_ready = True
            st.session_state.mcp_error = None
        except Exception as e:
            st.session_state.mcp_error = str(e)


# ==========================================================
# Header
# ==========================================================

st.markdown(
    """
    <div class='hero-card'>
        <h1>Enterprise AI Assistant</h1>
        <p>Ask business questions in natural language and let the assistant plan, execute, and summarize answers using CRM, Sales, and Finance tools.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# Layout
# ==========================================================

left_col, right_col = st.columns([1, 4])

# ==========================================================
# LEFT PANEL
# ==========================================================

with left_col:

    st.subheader("Planner")
    planner_placeholder = st.empty()
    planner_text = html.escape(st.session_state.planner_status)
    planner_placeholder.markdown(
        f"""
        <div class='status-card'>
            <h3>Planner</h3>
            <p>{planner_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Execution")
    execution_placeholder = st.empty()
    execution_text = html.escape(st.session_state.execution_status)
    execution_placeholder.markdown(
        f"""
        <div class='status-card'>
            <h3>Execution</h3>
            <p>{execution_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='min-height: 560px;'></div>", unsafe_allow_html=True)

# ==========================================================
# RIGHT PANEL
# ==========================================================

with right_col:

    st.subheader("Conversation")

    # A fixed-height container scopes chat_input to dock at the bottom
    # of THIS container (and this column's width) instead of the full
    # page width. Adjust height to taste.
    chat_area = st.container(height=700)

    with chat_area:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        query = st.chat_input(
            "Ask your business question...",
            disabled=not st.session_state.mcp_ready
        )

    if query:

        # --------------------------------------------------
        # Show User Message
        # --------------------------------------------------

        st.session_state.messages.append({"role": "user", "content": query})

        # --------------------------------------------------
        # Planner
        # --------------------------------------------------

        planner_placeholder.info("🧠 Planning...")
        execution_placeholder.info("Waiting for planner...")

        # --------------------------------------------------
        # Call Enterprise Graph (persistent instance + loop)
        # --------------------------------------------------

        result = run_async(
            st.session_state.enterprise_graph.run_query(
                user_query=query,
                history=st.session_state.conversation_history
            )
        )

        # Keep the real message-object history for the next turn.
        st.session_state.conversation_history = result["conversation_history"]

        # --------------------------------------------------
        # Planner Result
        # --------------------------------------------------

        st.session_state.planner_status = result["planner_result"]
        planner_placeholder.success(st.session_state.planner_status)

        # --------------------------------------------------
        # Execution Result
        # --------------------------------------------------

        if result["planned_actions"]:
            execution_text = "### Selected Tools\n\n"
            for tool in result["planned_actions"]:
                execution_text += f"✅ {tool['name']}\n\n"
            st.session_state.execution_status = execution_text
            execution_placeholder.success(st.session_state.execution_status)
        elif result["need_more_info"]:
            st.session_state.execution_status = "Waiting on clarification from you."
            execution_placeholder.info(st.session_state.execution_status)
        else:
            st.session_state.execution_status = "No tools selected."
            execution_placeholder.warning(st.session_state.execution_status)

        # --------------------------------------------------
        # Assistant Response
        #
        # If the planner needs more info, final_response is the
        # clarification question (set by ask_user_node). Otherwise
        # it's the summarized answer. Either way, the user's next
        # chat_input becomes the next turn automatically — no
        # special-casing needed here.
        # --------------------------------------------------

        answer = result.get("final_response") or "No response generated."

        st.session_state.messages.append({"role": "assistant", "content": answer})

        # One clean rerun redraws chat_area top-to-bottom in the correct
        # final order (input, then full message history) instead of us
        # manually painting bubbles mid-script.
        st.rerun()

# ==========================================================
# Footer
# ==========================================================

st.markdown(
    """
    <div class='footer-card'>
        <p><strong>Tip:</strong> Start with a specific business question like “What are our top revenue customers this quarter?” or “Show me open opportunities for customer ID CUST-001.”</p>
        <p><strong>Note:</strong> The assistant uses MCP tools from CRM, Finance, and Sales servers to deliver data-driven answers.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
