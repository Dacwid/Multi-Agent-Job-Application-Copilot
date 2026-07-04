import uuid

from fastapi import APIRouter, Depends, UploadFile

from app.auth import get_current_user_id
from app.services.resume_parser import extract_text
from app.services.supabase import get_supabase

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("")
async def upload_resume(
    file: UploadFile, user_id: str = Depends(get_current_user_id)
) -> dict:
    file_bytes = await file.read()
    extracted_text = extract_text(file_bytes, file.filename)

    storage_path = f"{user_id}/{uuid.uuid4()}-{file.filename}"
    supabase = get_supabase()
    supabase.storage.from_("resumes").upload(
        storage_path, file_bytes, {"content-type": file.content_type}
    )

    result = (
        supabase.table("resumes")
        .insert(
            {
                "user_id": user_id,
                "storage_path": storage_path,
                "extracted_text": extracted_text,
            }
        )
        .execute()
    )
    return result.data[0]
