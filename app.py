import sys
import os
import torch
from langchain_core.messages import HumanMessage, AIMessage

# Add project root (parent of this file) to sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
torch.classes.__path__ = [] 

import streamlit as st
import uuid
from main import build_graph

# Build LangGraph
graph = build_graph()

st.title("💬 Gmail Calendar Assistant")

# ------------------------
# ✅ Initialize session state
# ------------------------
if "sessions" not in st.session_state:
    st.session_state.sessions = {}

if "current_session" not in st.session_state:
    # Create a default session
    default_session_id = str(uuid.uuid4())
    st.session_state.sessions[default_session_id] = []
    st.session_state.current_session = default_session_id


# ------------------------
# ➕ Sidebar: New chat and session switcher
# ------------------------
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
    key="session_selector",  # <--- Important: separate state key
)

# Sync selected session
if selected_session != st.session_state.current_session:
    st.session_state.current_session = selected_session
    st.rerun()  # <-- Force rerun immediately after switch




# ------------------------
# 📜 Get messages for current session
# ------------------------
session_id = st.session_state.current_session
messages = st.session_state.sessions[session_id]

# Display past messages
for msg in messages:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    else:
        st.chat_message("assistant").write(msg.content)

# ------------------------
# 💬 User input and response
# ------------------------

user_query = st.chat_input("Type your message here...")
if user_query:
    st.chat_message("user").write(user_query)   
    messages.append(HumanMessage(user_query))
    # Keep last 8 messages for context
    context_messages = messages[-8:]



    # LangGraph state input
    state = {"messages": context_messages}

    # Run graph
    result = graph.invoke(state)

    # Get and display assistant response
    response = result["messages"][-1].content
    

    messages.append(AIMessage(response))
    
    st.chat_message("assistant").write(response)
