"""Session APIs: create, list, detail, and the SSE workflow run/resume endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.deps import RunCreds, get_run_creds
from app.db import repository
from app.services.runner import run_workflow_events

router = APIRouter()


class CreateSessionBody(BaseModel):
    company_name: str = Field(min_length=1)
    website: str = ""
    objective: str = ""


@router.post("/sessions", status_code=201)
def create_session(body: CreateSessionBody):
    return repository.create_session(
        company_name=body.company_name.strip(),
        website=body.website.strip(),
        objective=body.objective.strip(),
    )


@router.get("/sessions")
def list_sessions():
    return repository.list_sessions()


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/run")
async def run_session(
    session_id: str,
    request: Request,
    creds: RunCreds = Depends(get_run_creds),
):
    session = repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    graph = request.app.state.graph

    async def event_gen():
        async for event in run_workflow_events(
            session,
            provider=creds.provider,
            llm_key=creds.llm_key,
            tavily_key=creds.tavily_key,
            model=creds.model,
            graph=graph,
        ):
            if await request.is_disconnected():
                # Stop consuming the stream; node-level state is already persisted
                # in the checkpointer, so a later /run resumes where we left off.
                break
            yield event

    return EventSourceResponse(event_gen())
