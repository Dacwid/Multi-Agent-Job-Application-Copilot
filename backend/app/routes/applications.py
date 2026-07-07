import json
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel

from app.agents.events import register_queue, unregister_queue
from app.agents.graph import get_graph
from app.auth import get_current_user_id
from app.services.supabase import get_supabase

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateApplication(BaseModel):
    job_posting_text: str
    resume_id: str
    job_title: str | None = None
    company: str | None = None


class RejectDraft(BaseModel):
    feedback: str


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


@router.get("")
def list_applications(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    supabase = get_supabase()
    applications = (
        supabase.table("applications")
        .select("id,job_title,company,status,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    if not applications:
        return []

    app_ids = [a["id"] for a in applications]
    match_reports = (
        supabase.table("artifacts")
        .select("application_id,version,content")
        .in_("application_id", app_ids)
        .eq("kind", "match_report")
        .execute()
        .data
    )

    latest_version_by_app: dict[str, int] = {}
    latest_score_by_app: dict[str, int] = {}
    for artifact in match_reports:
        app_id = artifact["application_id"]
        if app_id not in latest_version_by_app or artifact["version"] > latest_version_by_app[app_id]:
            latest_version_by_app[app_id] = artifact["version"]
            latest_score_by_app[app_id] = artifact["content"]["match_score"]

    for application in applications:
        application["match_score"] = latest_score_by_app.get(application["id"])

    return applications


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


def _mark_latest_artifacts_approved(supabase, application_id: str) -> None:
    for kind in ("cover_letter", "interview_prep"):
        latest = (
            supabase.table("artifacts")
            .select("id")
            .eq("application_id", application_id)
            .eq("kind", kind)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            supabase.table("artifacts").update({"approved": True}).eq(
                "id", latest.data[0]["id"]
            ).execute()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _stream_graph_run(application_id: str, invoke_input):
    supabase = get_supabase()
    config = {"configurable": {"thread_id": application_id}}

    def event_stream():
        q = register_queue(application_id)
        outcome: dict = {}

        def run_graph():
            try:
                supabase.table("applications").update({"status": "running"}).eq(
                    "id", application_id
                ).execute()
                outcome["result"] = get_graph().invoke(invoke_input, config)
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
            return

        result = outcome["result"]
        interrupts = result.get("__interrupt__")
        if interrupts:
            supabase.table("applications").update({"status": "awaiting_approval"}).eq(
                "id", application_id
            ).execute()
            yield _sse(
                {
                    "type": "awaiting_approval",
                    "cover_letter": result["cover_letter"],
                    "interview_prep": result["interview_prep"],
                    "critic_feedback": result["critic_feedback"],
                    "revision_count": result["revision_count"],
                }
            )
            return

        _mark_latest_artifacts_approved(supabase, application_id)
        supabase.table("applications").update({"status": "completed"}).eq(
            "id", application_id
        ).execute()
        yield _sse(
            {
                "type": "done",
                "job_analysis": result["job_analysis"],
                "match_report": result["match_report"],
                "cover_letter": result["cover_letter"],
                "interview_prep": result["interview_prep"],
                "critic_feedback": result["critic_feedback"],
                "revision_count": result["revision_count"],
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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

    initial_state = {
        "application_id": application_id,
        "job_posting": application["job_posting_text"],
        "resume_text": resume.data[0]["extracted_text"],
        "job_analysis": None,
        "match_report": None,
        "cover_letter": None,
        "interview_prep": None,
        "critic_feedback": None,
        "revision_count": 0,
        "human_review_started": False,
        "approved": False,
    }
    return _stream_graph_run(application_id, initial_state)


@router.post("/{application_id}/approve")
def approve_application(application_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    application = _get_owned_application(supabase, application_id, user_id)
    if application["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Application is not awaiting approval")

    return _stream_graph_run(application_id, Command(resume={"action": "approve"}))


@router.post("/{application_id}/reject")
def reject_application(
    application_id: str, body: RejectDraft, user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    application = _get_owned_application(supabase, application_id, user_id)
    if application["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Application is not awaiting approval")

    return _stream_graph_run(
        application_id,
        Command(resume={"action": "request_changes", "feedback": body.feedback}),
    )


@router.post("/{application_id}/retry")
def retry_application(application_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    application = _get_owned_application(supabase, application_id, user_id)
    if application["status"] != "failed":
        raise HTTPException(status_code=400, detail="Application has not failed")

    # Passing None resumes from the last successful checkpoint instead of
    # starting over, re-running only the node(s) that failed.
    return _stream_graph_run(application_id, None)
