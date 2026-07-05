from app.schemas.interview_prep import InterviewPrep
from app.services.llm import generate_structured

PROMPT_TEMPLATE = """Based on this job analysis and match report, generate likely interview questions
and suggested talking points for the candidate. Ground talking points in the match report's strengths
and gaps — do not invent experience.

Job analysis:
{job_analysis}

Match report:
{match_report}

Produce 4-6 likely interview questions, each with 2-3 suggested talking points.
"""


def prepare_interview(job_analysis: dict, match_report: dict) -> InterviewPrep:
    prompt = PROMPT_TEMPLATE.format(job_analysis=job_analysis, match_report=match_report)
    return generate_structured(prompt, InterviewPrep)
