from pydantic import BaseModel


class InterviewQuestion(BaseModel):
    question: str
    talking_points: list[str]


class InterviewPrep(BaseModel):
    questions: list[InterviewQuestion]
