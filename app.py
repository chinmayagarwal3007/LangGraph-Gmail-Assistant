import sys
import os
import torch
from langchain_core.messages import HumanMessage, AIMessage
from google_services import get_credentials_from_code, get_auth_url, get_service
from main import get_tool_node

# Add project root (parent of this file) to sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
torch.classes.__path__ = [] 

import streamlit as st
import uuid
from main import build_graph

query_params = st.query_params

st.title("💬 Gmail Calendar Assistant")

# 🔐 Initialize session state for credentials
if "credentials" not in st.session_state:
    st.session_state["credentials"] = None

# Authentication block
if st.session_state.credentials is None:
    st.markdown("### 🔐 Connect your Gmail & Calendar")
    if st.button("🔗 Connect with Google"):
        auth_url = get_auth_url()
        st.session_state.auth_url = auth_url
        st.markdown(f"[Click here to authorize]({auth_url})")

    if "code" in query_params:
        code_val = query_params["code"]
        creds = get_credentials_from_code(code_val)
        st.session_state.credentials = creds
        st.success("🎉 Successfully authenticated!")
        st.toast("✅ You're connected! Now use your Assistant ✨", icon="🎉")
        st.rerun()

# ----------------------
# 🧠 Only show chatbot AFTER auth
# ----------------------
else:
    gmail_service = get_service("gmail", st.session_state.credentials)
    calendar_service = get_service("calendar", st.session_state.credentials)
    tool_node = get_tool_node(gmail_service, calendar_service)
    graph = build_graph(tool_node)

    

    # 🧠 LangGraph state + session logic
    if "sessions" not in st.session_state:
        st.session_state.sessions = {}

    if "current_session" not in st.session_state:
        default_session_id = str(uuid.uuid4())
        st.session_state.sessions[default_session_id] = []
        st.session_state.current_session = default_session_id

    if st.sidebar.button("➕ New Chat"):
        new_session_id = str(uuid.uuid4())
        st.session_state.sessions[new_session_id] = []
        st.session_state.current_session = new_session_id

    session_ids = list(st.session_state.sessions.keys())
    if session_ids:
        selected_session = st.sidebar.radio(
            "Select a session:",
            session_ids,
            index=session_ids.index(st.session_state.current_session),
            format_func=lambda s: f"Session {session_ids.index(s)+1}",
            key="session_selector",
        )

    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.rerun()

    session_id = st.session_state.current_session
    messages = st.session_state.sessions[session_id]

    for msg in messages:
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        else:
            st.chat_message("assistant").write(msg.content)

    user_query = st.chat_input("Type your message here...")
    if user_query:
        st.chat_message("user").write(user_query)
        messages.append(HumanMessage(user_query))

        context_messages = messages[-8:]
        state = {"messages": context_messages}
        result = graph.invoke(state)
        response = result["messages"][-1].content

        messages.append(AIMessage(response))
        st.chat_message("assistant").write(response)
