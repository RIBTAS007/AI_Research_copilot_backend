"""Chat API: actionable, report-grounded follow-up chat over SSE."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api.deps import LLMCreds, get_llm_creds
from app.db import repository
from app.services.chat import chat_stream

router = APIRouter()


class ChatBody(BaseModel):
    message: str = ""
    action: str | None = None   # expand_section | challenge_insight | generate_email
    target: str | None = None   # section key / insight text for the action


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    if not repository.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return repository.get_messages(session_id)


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: str,
    body: ChatBody,
    request: Request,
    creds: LLMCreds = Depends(get_llm_creds),
):
    session = repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("report"):
        raise HTTPException(status_code=409, detail="Run the research workflow first.")
    if not body.message and not body.action:
        raise HTTPException(status_code=400, detail="Provide a message or an action.")

    async def event_gen():
        async for event in chat_stream(
            session,
            message=body.message,
            action=body.action,
            target=body.target,
            provider=creds.provider,
            llm_key=creds.llm_key,
            model=creds.model,
        ):
            if await request.is_disconnected():
                break
            yield event

    return EventSourceResponse(event_gen())
