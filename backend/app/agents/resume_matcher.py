from app.schemas.match_report import MatchReport
from app.services.llm import generate_structured

PROMPT_TEMPLATE = """You are comparing a candidate's resume against a job analysis to produce a match report.
Ground every claim strictly in the resume text below — never invent experience the candidate doesn't have.

Job analysis:
{job_analysis}

Resume:
---
{resume}
---

Produce:
- match_score: 0-100, how well the resume matches the role
- strengths: specific resume points that align with the role
- gaps: required or nice-to-have skills from the job analysis not evidenced in the resume
- suggestions: concrete, specific ways the candidate could improve their resume or application for this role
"""


def match_resume(job_analysis: dict, resume_text: str) -> MatchReport:
    prompt = PROMPT_TEMPLATE.format(job_analysis=job_analysis, resume=resume_text)
    return generate_structured(prompt, MatchReport)
