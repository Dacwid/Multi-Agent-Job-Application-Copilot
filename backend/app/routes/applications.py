import json
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.events import register_queue, unregister_queue
from app.agents.graph import graph
from app.auth import get_current_user_id
from app.services.supabase import get_supabase

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateApplication(BaseModel):
    job_posting_text: str
    resume_id: str
    job_title: str | None = None
    company: str | None = None


@router.post("")
def create_application(
    body: CreateApplication, user_id: str = Depends(get_current_user_id)
) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("applications")
        .insert(
            {
                "user_id": user_id,
                "resume_id": body.resume_id,
                "job_posting_text": body.job_posting_text,
                "job_title": body.job_title,
                "company": body.company,
            }
        )
        .execute()
    )
    return result.data[0]


def _get_owned_application(supabase, application_id: str, user_id: str) -> dict:
    result = (
        supabase.table("applications")
        .select("*")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.get("/{application_id}/run/stream")
def stream_application_run(application_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    application = _get_owned_application(supabase, application_id, user_id)

    resume = (
        supabase.table("resumes")
        .select("extracted_text")
        .eq("id", application["resume_id"])
        .eq("user_id", user_id)
        .execute()
    )
    if not resume.data:
        raise HTTPException(status_code=404, detail="Resume not found")

    def event_stream():
        q = register_queue(application_id)
        outcome: dict = {}

        def run_graph():
            try:
                supabase.table("applications").update({"status": "running"}).eq(
                    "id", application_id
                ).execute()
                outcome["final_state"] = graph.invoke(
                    {
                        "application_id": application_id,
                        "job_posting": application["job_posting_text"],
                        "resume_text": resume.data[0]["extracted_text"],
                        "job_analysis": None,
                        "match_report": None,
                        "cover_letter": None,
                        "interview_prep": None,
                        "critic_feedback": None,
                        "revision_count": 0,
                    }
                )
                supabase.table("applications").update({"status": "completed"}).eq(
                    "id", application_id
                ).execute()
            except Exception as exc:
                supabase.table("applications").update({"status": "failed"}).eq(
                    "id", application_id
                ).execute()
                outcome["error"] = str(exc)
            finally:
                q.put({"type": "__stream_done__"})

        thread = threading.Thread(target=run_graph, daemon=True)
        thread.start()

        try:
            while True:
                event = q.get()
                if event["type"] == "__stream_done__":
                    break
                yield _sse(event)
        finally:
            unregister_queue(application_id)

        if "error" in outcome:
            yield _sse({"type": "error", "message": outcome["error"]})
        else:
            final_state = outcome["final_state"]
            yield _sse(
                {
                    "type": "done",
                    "job_analysis": final_state["job_analysis"],
                    "match_report": final_state["match_report"],
                    "cover_letter": final_state["cover_letter"],
                    "interview_prep": final_state["interview_prep"],
                    "critic_feedback": final_state["critic_feedback"],
                    "revision_count": final_state["revision_count"],
                }
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
