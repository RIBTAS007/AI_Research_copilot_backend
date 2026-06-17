"""FastAPI application entrypoint.

Lifespan wires up: the relational DB, the async SQLite checkpointer (for graph
recoverability), and the compiled LangGraph workflow (held on app.state).
"""
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat as chat_api
from app.api import config as config_api
from app.api import sessions as sessions_api
from app.config import settings
from app.db.database import init_db
from app.graph.build import build_graph
from app.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    init_db()
    conn = await aiosqlite.connect(settings.checkpoint_db)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    app.state.checkpoint_conn = conn
    app.state.graph = build_graph(checkpointer=saver)
    log.info("Startup complete — graph compiled with checkpointer.")
    try:
        yield
    finally:
        await conn.close()
        log.info("Shutdown complete.")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

# CORS: defaults to "*" (allow all) so deployment "just works"; restrict to your
# Vercel/Render URL later by setting CORS_ORIGINS="https://your-app.vercel.app".
# allow_credentials stays False on purpose: keys are sent as custom headers (BYOK),
# not cookies, and the spec forbids wildcard origin together with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(config_api.router, tags=["config"])
app.include_router(sessions_api.router, tags=["sessions"])
app.include_router(chat_api.router, tags=["chat"])
