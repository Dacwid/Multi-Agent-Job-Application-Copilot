from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


@router.post("/{application_id}/run")
def run_application(
    application_id: str, user_id: str = Depends(get_current_user_id)
) -> dict:
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

    supabase.table("applications").update({"status": "running"}).eq(
        "id", application_id
    ).execute()

    try:
        final_state = graph.invoke(
            {
                "application_id": application_id,
                "job_posting": application["job_posting_text"],
                "resume_text": resume.data[0]["extracted_text"],
                "job_analysis": None,
                "match_report": None,
                "cover_letter": None,
                "interview_prep": None,
            }
        )
    except Exception:
        supabase.table("applications").update({"status": "failed"}).eq(
            "id", application_id
        ).execute()
        raise

    supabase.table("applications").update({"status": "completed"}).eq(
        "id", application_id
    ).execute()

    return {
        "job_analysis": final_state["job_analysis"],
        "match_report": final_state["match_report"],
        "cover_letter": final_state["cover_letter"],
        "interview_prep": final_state["interview_prep"],
    }
