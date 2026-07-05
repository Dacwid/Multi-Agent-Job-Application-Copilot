from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.job_analyst import analyze_job_posting
from app.auth import get_current_user_id
from app.services.supabase import get_supabase

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateApplication(BaseModel):
    job_posting_text: str
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


@router.post("/{application_id}/analyze")
def analyze_application(
    application_id: str, user_id: str = Depends(get_current_user_id)
) -> dict:
    supabase = get_supabase()
    application = _get_owned_application(supabase, application_id, user_id)

    analysis = analyze_job_posting(application["job_posting_text"])

    artifact = (
        supabase.table("artifacts")
        .insert(
            {
                "application_id": application_id,
                "kind": "job_analysis",
                "content": analysis.model_dump(),
            }
        )
        .execute()
    )
    supabase.table("applications").update({"status": "completed"}).eq(
        "id", application_id
    ).execute()

    return artifact.data[0]
