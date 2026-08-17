"""
chat_sessions.py

File-backed chat session storage for the Streamlit app. Solves two things:

1. st.session_state doesn't survive a real page refresh — it's server
   memory tied to one browser connection, wiped on reload. Persisting to
   disk and loading on session start fixes that.
2. "Multiple named chats you can switch between" needs something to switch
   BETWEEN — each chat is a JSON file on disk, listed/created/loaded here.

One JSON file per session in data/chat_sessions/, named by session ID.

Known limitation, worth being upfront about: there's no user/auth
separation here. On a shared hosted server with multiple teams (Ops, AIV),
everyone hitting the same instance sees the SAME list of chats and can
open/rename/delete any of them — there's no privacy between users yet.
Fine for now given the current trust level, but worth fixing before this
scales further (see add_user_tag below for the smallest possible step
toward that, not wired in by default).
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import json
import re
import uuid

SESSIONS_DIR = Path(__file__).resolve().parents[1] / "data" / "chat_sessions"


@dataclass
class ChatSession:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[dict]  # [{"role": "user"|"assistant", "content": "..."}]


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _slugify_title(text: str, max_len: int = 40) -> str:
    text = text.strip().replace("\n", " ")
    return (text[:max_len] + "…") if len(text) > max_len else text


def list_sessions() -> List[ChatSession]:
    """Returns all sessions, most recently updated first."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path) as f:
                sessions.append(ChatSession(**json.load(f)))
        except (json.JSONDecodeError, TypeError):
            continue  # skip corrupted files rather than crash the whole list
    return sorted(sessions, key=lambda s: s.updated_at, reverse=True)


def create_session(title: Optional[str] = None) -> ChatSession:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    session = ChatSession(
        id=str(uuid.uuid4()),
        title=title or "New chat",
        created_at=now,
        updated_at=now,
        messages=[],
    )
    _save(session)
    return session


def load_session(session_id: str) -> Optional[ChatSession]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    with open(path) as f:
        return ChatSession(**json.load(f))


def _save(session: ChatSession) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_session_path(session.id), "w") as f:
        json.dump(asdict(session), f, indent=2)


def append_message(session_id: str, role: str, content: str) -> ChatSession:
    session = load_session(session_id)
    if session is None:
        raise ValueError(f"No session with id {session_id}")

    session.messages.append({"role": role, "content": content})
    session.updated_at = datetime.now(timezone.utc).isoformat()

    # Auto-title from the first user message, so "New chat" doesn't linger
    # in the sidebar forever once there's real content to name it from.
    if session.title == "New chat" and role == "user":
        session.title = _slugify_title(content)

    _save(session)
    return session


def rename_session(session_id: str, new_title: str) -> Optional[ChatSession]:
    session = load_session(session_id)
    if session is None:
        return None
    session.title = new_title
    session.updated_at = datetime.now(timezone.utc).isoformat()
    _save(session)
    return session


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False