import streamlit as st
# Import your exact pipeline class from the src folder
from rag import RagPipeline

# Set up the browser tab title and layouts
st.set_page_config(page_title="MeerKAT Ops & AIV Assistant", page_icon="🔭")
st.title("🔭 MeerKAT/SKA-Low Diagnostic Assistant")
st.caption("Tier 1 (RAG Q&A) — Fully Local & Secure")

# Cache the pipeline instantiation so it only runs ONCE when the server starts.
# This prevents the app from re-loading models every time someone clicks a button.
@st.cache_resource
def load_pipeline():
    return RagPipeline()

pipeline = load_pipeline()

# Initialize chat history in browser session memory if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages on the screen if the user refreshes or keeps typing
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# This replaces the `while True: question = input("> ")` loop with a browser text box
if question := st.chat_input("Ask about an error log, system manual step, or JIRA resolution..."):
    
    # 1. Display what the user typed in the chat window
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    # 2. Feed the question into your exact pipeline and display a loading spinner
    with st.spinner("Analyzing documentation and generating response..."):
        # This calls your exact pipeline.ask() logic
        response = pipeline.ask(question)

    # 3. Display the response in the chat window
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
