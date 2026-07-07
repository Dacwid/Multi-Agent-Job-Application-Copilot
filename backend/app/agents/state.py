from typing import TypedDict


class AppState(TypedDict):
    application_id: str
    job_posting: str
    resume_text: str
    job_analysis: dict | None
    match_report: dict | None
    cover_letter: dict | None
    interview_prep: dict | None
    critic_feedback: dict | None
    revision_count: int
    human_review_started: bool
    approved: bool
