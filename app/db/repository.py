"""Thin data-access layer. Each call opens and closes its own DB session so it is
safe to invoke from async request handlers and streaming generators."""
from contextlib import contextmanager
from typing import Iterator

from app.db.database import SessionLocal
from app.db.models import CacheEntry, Message, Session, WorkflowEvent


@contextmanager
def _db() -> Iterator:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --- sessions --------------------------------------------------------------

def create_session(company_name: str, website: str, objective: str) -> dict:
    with _db() as db:
        s = Session(company_name=company_name, website=website, objective=objective)
        db.add(s)
        db.flush()
        return _session_to_dict(s)


def list_sessions() -> list[dict]:
    with _db() as db:
        rows = db.query(Session).order_by(Session.created_at.desc()).all()
        return [_session_to_dict(s, include_report=False) for s in rows]


def get_session(session_id: str) -> dict | None:
    with _db() as db:
        s = db.get(Session, session_id)
        if not s:
            return None
        data = _session_to_dict(s)
        data["events"] = [_event_to_dict(e) for e in s.events]
        data["messages"] = [_message_to_dict(m) for m in s.messages]
        return data


def update_status(session_id: str, status: str, error: str | None = None) -> None:
    with _db() as db:
        s = db.get(Session, session_id)
        if s:
            s.status = status
            if error is not None:
                s.error = error


def save_report(session_id: str, report: dict, run_meta: dict | None = None) -> None:
    with _db() as db:
        s = db.get(Session, session_id)
        if s:
            s.report = report
            if run_meta is not None:
                s.run_meta = run_meta


# --- workflow events -------------------------------------------------------

def add_event(
    session_id: str,
    node: str,
    status: str,
    message: str,
    duration_ms: int = 0,
    tokens: int = 0,
) -> None:
    with _db() as db:
        db.add(
            WorkflowEvent(
                session_id=session_id,
                node=node,
                status=status,
                message=message,
                duration_ms=duration_ms,
                tokens=tokens,
            )
        )


def clear_events(session_id: str) -> None:
    with _db() as db:
        db.query(WorkflowEvent).filter(
            WorkflowEvent.session_id == session_id
        ).delete()


# --- chat messages ---------------------------------------------------------

def add_message(session_id: str, role: str, content: str) -> dict:
    with _db() as db:
        m = Message(session_id=session_id, role=role, content=content)
        db.add(m)
        db.flush()
        return _message_to_dict(m)


def get_messages(session_id: str) -> list[dict]:
    with _db() as db:
        rows = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at)
            .all()
        )
        return [_message_to_dict(m) for m in rows]


# --- cache -----------------------------------------------------------------

def cache_get(key: str) -> dict | None:
    with _db() as db:
        row = db.get(CacheEntry, key)
        return row.value if row else None


def cache_set(key: str, value: dict) -> None:
    with _db() as db:
        row = db.get(CacheEntry, key)
        if row:
            row.value = value
        else:
            db.add(CacheEntry(key=key, value=value))


# --- serialisers -----------------------------------------------------------

def _session_to_dict(s: Session, include_report: bool = True) -> dict:
    data = {
        "id": s.id,
        "company_name": s.company_name,
        "website": s.website,
        "objective": s.objective,
        "status": s.status,
        "error": s.error,
        "run_meta": s.run_meta,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
    if include_report:
        data["report"] = s.report
    return data


def _event_to_dict(e: WorkflowEvent) -> dict:
    return {
        "id": e.id,
        "node": e.node,
        "status": e.status,
        "message": e.message,
        "duration_ms": e.duration_ms,
        "tokens": e.tokens,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _message_to_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
