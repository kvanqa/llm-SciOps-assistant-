import streamlit as st

# Import your exact pipeline class from the src folder
from rag import RagPipeline
import chat_sessions as cs

# Set up the browser tab title and layouts
st.set_page_config(page_title="SKAO RAG Assistant tool", page_icon="🔭")


# Cache the pipeline instantiation so it only runs ONCE when the server starts.
# This prevents the app from re-loading models every time someone clicks a button.
@st.cache_resource
def load_pipeline():
    return RagPipeline()


pipeline = load_pipeline()

# --- Sidebar: chat list, new chat, rename/delete for the active chat ---

st.sidebar.title("Chats")

if st.sidebar.button("+ New chat", use_container_width=True):
    new_session = cs.create_session()
    st.session_state.current_session_id = new_session.id
    st.rerun()

sessions = cs.list_sessions()
for session in sessions:
    is_active = st.session_state.get("current_session_id") == session.id
    label = f"**{session.title}**" if is_active else session.title
    if st.sidebar.button(label, key=f"session_{session.id}", use_container_width=True):
        st.session_state.current_session_id = session.id
        st.rerun()

# Make sure a session is always selected — first-ever load, or after the
# active one gets deleted below.
if "current_session_id" not in st.session_state or not cs.load_session(
    st.session_state.current_session_id
):
    if sessions:
        st.session_state.current_session_id = sessions[0].id
    else:
        st.session_state.current_session_id = cs.create_session().id

current = cs.load_session(st.session_state.current_session_id)

st.sidebar.divider()
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Rename", use_container_width=True):
        st.session_state.show_rename = True
with col2:
    if st.button("Delete", use_container_width=True):
        cs.delete_session(current.id)
        remaining = cs.list_sessions()
        st.session_state.current_session_id = remaining[0].id if remaining else cs.create_session().id
        st.rerun()

if st.session_state.get("show_rename"):
    new_title = st.sidebar.text_input("New title", value=current.title)
    if st.sidebar.button("Save title"):
        cs.rename_session(current.id, new_title)
        st.session_state.show_rename = False
        st.rerun()

# --- Main chat area ---

st.title("🔭 SKAO RAG Assistant")
st.caption("Tier 1 (RAG Q&A) — Fully Local & Secure")

# Display past chat messages for the CURRENTLY SELECTED session, loaded
# from disk — not st.session_state.messages, which is why this now
# survives a real page refresh and supports multiple named chats.
for message in current.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# This replaces the `while True: question = input("> ")` loop with a browser text box
if question := st.chat_input("Ask about an error log, system manual step, or JIRA resolution..."):

    # 1. Display what the user typed, and persist it to this session's file
    with st.chat_message("user"):
        st.markdown(question)
    cs.append_message(current.id, "user", question)

    # 2. Feed the question into your exact pipeline and display a loading spinner
    with st.spinner("Analyzing documentation and generating response..."):
        response = pipeline.ask(question)

    # 3. Display the response, and persist it too
    with st.chat_message("assistant"):
        st.markdown(response)
    cs.append_message(current.id, "assistant", response)

    # Rerun so the sidebar picks up the auto-generated title (set from the
    # first user message) and the new message order.
    st.rerun()
    