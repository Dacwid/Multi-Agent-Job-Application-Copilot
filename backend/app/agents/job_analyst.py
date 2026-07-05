from app.schemas.job_analysis import JobAnalysis
from app.services.llm import generate_structured

PROMPT_TEMPLATE = """You are analyzing a job posting for a candidate preparing an application.
Extract the following from the posting text below, grounded only in what is stated or clearly implied:
- role_title: the job title
- seniority: e.g. intern, junior, mid, senior, staff, lead
- required_skills: skills explicitly listed as required
- nice_to_have_skills: skills listed as preferred/bonus
- keywords: notable terms worth echoing in a tailored application (tools, methodologies, domain terms)
- company_signals: anything about company culture, mission, or work style mentioned
- summary: a 2-3 sentence summary of the role

Job posting:
---
{posting}
---
"""


def analyze_job_posting(posting_text: str) -> JobAnalysis:
    prompt = PROMPT_TEMPLATE.format(posting=posting_text)
    return generate_structured(prompt, JobAnalysis)
