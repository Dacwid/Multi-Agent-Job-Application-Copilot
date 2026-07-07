"""Postgres-backed LangGraph checkpointer, needed for interrupt()/Command(resume=...)
to persist graph state across separate HTTP requests (Phase 6 human-in-the-loop)."""

from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings


@lru_cache
def get_checkpointer() -> PostgresSaver:
    pool = ConnectionPool(
        conninfo=settings.database_url,
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return checkpointer
