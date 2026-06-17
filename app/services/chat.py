"""Actionable follow-up chat, grounded on the stored report.

Supports free-form Q&A plus structured actions (expand a section, challenge an
insight, generate an outreach email). Answers stream token-by-token over SSE.
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.db import repository
from app.graph import prompts
from app.graph.format import report_to_blob
from app.graph.llm import build_llm
from app.logging_config import get_logger

log = get_logger("services.chat")


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


def _resolve_message(action: str | None, target: str | None, message: str, company: str) -> str:
    """Turn a quick-action into a concrete instruction, else use the raw message."""
    if action and action in prompts.CHAT_ACTIONS:
        return prompts.CHAT_ACTIONS[action].format(target=target or "", company=company)
    return message


async def chat_stream(
    session: dict,
    *,
    message: str,
    action: str | None,
    target: str | None,
    provider: str,
    llm_key: str,
    model: str | None,
):
    """Async generator yielding SSE token events for a chat turn."""
    session_id = session["id"]
    company = session["company_name"]

    try:
        llm = build_llm(provider, llm_key, model)
    except Exception as exc:
        yield _sse("error", {"message": f"Setup failed: {exc}"})
        return

    user_text = _resolve_message(action, target, message, company)
    repository.add_message(session_id, "user", user_text)

    system = prompts.chat_system_prompt(company, report_to_blob(session.get("report") or {}))
    history = repository.get_messages(session_id)[:-1]  # exclude the message just added
    msgs = [SystemMessage(content=system)]
    for m in history[-10:]:
        msgs.append(
            HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        )
    msgs.append(HumanMessage(content=user_text))

    full = ""
    try:
        async for chunk in llm.astream(msgs):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                full += token
                yield _sse("token", {"token": token})
    except Exception as exc:
        log.exception("chat stream failed for session %s", session_id)
        yield _sse("error", {"message": str(exc)})
        return

    repository.add_message(session_id, "assistant", full)
    yield _sse("done", {"content": full})
