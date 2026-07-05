"""Wraps a single agent call with an agent_runs audit row and an artifacts row.
Shared by every graph node so the timeline (agent_runs) and results (artifacts)
stay consistent without repeating the same bookkeeping four times."""

from datetime import datetime, timezone
from typing import Callable, TypeVar

from pydantic import BaseModel

from app.services.supabase import get_supabase

T = TypeVar("T", bound=BaseModel)


def run_agent(application_id: str, agent_name: str, kind: str, fn: Callable[[], T]) -> T:
    supabase = get_supabase()
    run = (
        supabase.table("agent_runs")
        .insert(
            {
                "application_id": application_id,
                "agent_name": agent_name,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
        .data[0]
    )

    try:
        result = fn()
    except Exception:
        supabase.table("agent_runs").update(
            {"status": "failed", "finished_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", run["id"]).execute()
        raise

    supabase.table("agent_runs").update(
        {
            "status": "completed",
            "output": result.model_dump(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", run["id"]).execute()

    supabase.table("artifacts").insert(
        {"application_id": application_id, "kind": kind, "content": result.model_dump()}
    ).execute()

    return result
