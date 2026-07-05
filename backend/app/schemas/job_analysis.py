from pydantic import BaseModel


class JobAnalysis(BaseModel):
    role_title: str
    seniority: str
    required_skills: list[str]
    nice_to_have_skills: list[str]
    keywords: list[str]
    company_signals: list[str]
    summary: str
