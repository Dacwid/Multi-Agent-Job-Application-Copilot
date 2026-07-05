from pydantic import BaseModel


class CriticFeedback(BaseModel):
    cover_letter_pass: bool
    cover_letter_score: int
    cover_letter_feedback: list[str]
    interview_prep_pass: bool
    interview_prep_score: int
    interview_prep_feedback: list[str]
