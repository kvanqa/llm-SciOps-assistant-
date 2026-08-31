import streamlit as st
import requests
# from datetime import datetime, timedelta
from ticket_data_utils import summarize_fetch_window

# 1. IMPORT YOUR JIRA CLIENT CODE
from jira_client import build_jira_client

# Import your exact pipeline class from the src folder
from rag import RagPipeline
import chat_sessions as cs


# Set up the browser tab title and layouts
st.set_page_config(page_title="RAG-based LLM Assistant tool", page_icon="🔭")
st.title("SciOps Tier-2 Assistant")

# Cache the pipeline instantiation so it only runs ONCE when the server starts.
# This prevents the app from re-loading models every time someone clicks a button.
# @st.cache_resource
# def load_pipeline():
#     return RagPipeline()


pipeline = RagPipeline()
# Initialize the live Jira client (reads env variables automatically)
# Change to mode="mock" if you want to test with dummy JSON files locally
jira = build_jira_client(mode="live")
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

st.title("🔭 RAG-based LLM Assistant")
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
    with st.spinner("Analyzing documentation, jira context and generating response..."):
        # 1. Fetch tickets from the last 3 days to make sure we grab older updates/fixes
        from datetime import datetime, timedelta
        since = datetime.now() - timedelta(days=3)
        tickets = jira.fetch_tickets(since=since, project_key="OPS")

        # 2. Build a highly visible, structured text block
        if tickets:
            jira_context = "\n---\n".join([t.to_context_text() for t in tickets])
        else:
            jira_context = "No recent Jira tickets found in the OPS project."
        
        # NEW: explicit count + window enchor -- fixes the undercounting
        # (asked for "all tickets in past 2 days", model found only 1 of 12
        # actually present, even though every fetched ticket already
        # satisfies that constraint by construction of the fetch itself).
        fetch_window_note = summarize_fetch_window(tickets, since)

        #DEBUG CHECK: This lets you verify exactly what text leaves Jira in your terminal window
        print("=== DEBUG JIRA CONTEXT GOING TO RAG PIPELINE ===")
        print(jira_context)
        print("================================================")
        
        # 3. Retrieve document context using ONLY the clean question --
        #    NOT master_prompt/jira_context. This is the fix for retrieval
        #    pollution: pipeline.ask() would otherwise use the WHOLE prompt
        #    (including all the ticket text) as the document search query,
        #    drowning out the actual question and pulling back irrelevant
        #    document chunks.
        #
        #    Uses pipeline.db.ops_collection directly (SKAChromaManager's
        #    real interface) -- not a .backend.search() wrapper, which
        #    doesn't exist on this class. ops_collection specifically,
        #    not icd_collection, since this is operator Q&A.
        doc_results = pipeline.db.ops_collection.query(
            query_texts=[question], n_results=pipeline.top_k
        )
        print(f"number of docs found: {pipeline.db.ops_collection.count()}")
        docs = doc_results.get("documents", [[]])[0]
        metas = doc_results.get("metadatas", [[]])[0]
        doc_context = "\n\n".join(
            f"[Source: {m.get('source', 'unknown')}]\n{d}" for d, m in zip(docs, metas)
        ) if docs else "No relevant document passages found."
      
        # 4. THE FIX: build a real messages array instead of one hand-formatted
        #    prompt string with Llama-3-specific tokens baked in. Those
        #    tokens (<|begin_of_text|>, <|start_header_id|>, etc.) are
        #    meaningless to Qwen -- and since Ollama's /api/generate applies
        #    the CURRENTLY LOADED MODEL'S OWN template on top of whatever
        #    you send (unless raw=true), your hand-built Llama-3 tokens were
        #    getting wrapped a second time inside Qwen's native ChatML
        #    template -- doubly garbled, no real structural separation
        #    between instructions/context/question from the model's point
        #    of view. Using /api/chat with role-tagged messages lets Ollama
        #    apply whichever template is ACTUALLY correct for whatever
        #    model is loaded -- this fix survives future model swaps too.
        system_content = f"""You are the MeerKAT SciOps Assistant. You are provided with static manual data and deep rich details for the most relevant tickets matching the query.

DEEP RICH TICKET DETAILS (REPORTER, ASSIGNEE, DESCRIPTION, COMMENTS):
{jira_context}

STATIC MANUAL DATA:
{doc_context}

CRITICAL RULES:
- The terms "Reporter", "Creator", "Submitter", "Reported By", and "Created By" mean the EXACT same thing. Use the name listed next to "Reporter/Creator" to answer any question about who reported, submitted, or created a ticket.
- Ignore minor spelling differences or typos in names (e.g., treat 'Lavishini' and 'Lavashni' as the exact same person).
- When asked for a summary of tickets by a specific person, scan the "Reporter/Creator:" fields, find all matches, and list their corresponding "Summary:" strings clearly.
- Do not claim information is missing if a name is visible in the context block.
- STATIC MANUAL DATA is the authoritative source for operational procedures, commands, configuration instructions, and "how to" questions.
- If the answer to the user's question is present in STATIC MANUAL DATA,use that information directly.
- JIRA DATA should primarily be used for ticket history, incidents, reporters, assignees, comments, dates, and other historical information.
- Do not use unrelated Jira information to answer a documentation or procedural question.
- Do not say information is missing when it is explicitly present in STATIC MANUAL DATA.
- Answer using ONLY the STATIC MANUAL DATA and DEEP RICH TICKET DETAILS above. Never invent, paraphrase from memory, or generate content not present in this context -- if asked to cite a source and the information came from the context above, cite it exactly; if it's not in the context, say so explicitly rather than generating a plausible-sounding answer.
- Count carefully: if asked "how many" or "all tickets matching X", check the FETCH WINDOW note above and scan every ticket block, not just the first one.
{fetch_window_note}
"""

        # 5. Recent conversation as REAL message turns, not text stuffed into
        #    the system prompt -- models handle actual role-tagged history
        #    more reliably than a description of history in prose.
        recent_history = current.messages[-3:] if current.messages else []
        chat_messages = [{"role": "system", "content": system_content}]
        for m in recent_history:
            role = "assistant" if m["role"] == "assistant" else "user"
            chat_messages.append({"role": role, "content": m["content"]})
        chat_messages.append({"role": "user", "content": question})

        # 6. Call /api/chat, not /api/generate.
        #    num_ctx is critical here: Ollama defaults to ~2048-4096 tokens
        #    and SILENTLY truncates anything beyond that from the START of
        #    the prompt, with no error. STATIC MANUAL DATA sits early in
        #    system_content -- exactly what gets dropped first once the
        #    combined prompt (manual excerpts + ticket details + rules +
        #    history) exceeds the default. 8192 is a safe starting point
        #    for qwen3:14b on 24GB unified memory; raise further if prompts
        #    are still getting cut (check the response's prompt_eval_count
        #    against your actual prompt length to confirm whether this is
        #    still happening)
        resp = requests.post(
            f"{pipeline.provider.host}/api/chat",
            json={
                "model": pipeline.provider.model,
                "messages": chat_messages,
                "stream": False,
                "options": {"temperature": pipeline.provider.temperature,"num_ctx": 8192},
            },
            timeout=120,
        )
        resp.raise_for_status()
        response = resp.json().get("message", {}).get("content", "").strip()

        print("\n===== RETRIEVED DOCUMENTS =====")
        print("\n===== doc_context =====")
        print(doc_context)
        print("===== END RETRIEVED DOCUMENTS =====\n")

    # 3. Display the response, and persist it too
    with st.chat_message("assistant"):
        st.markdown(response)
    cs.append_message(current.id, "assistant", response)

    # Rerun so the sidebar picks up the auto-generated title (set from the
    # first user message) and the new message order.
    st.rerun()
    