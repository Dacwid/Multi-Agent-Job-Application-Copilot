from app.schemas.critic_feedback import CriticFeedback
from app.services.llm import generate_structured

PROMPT_TEMPLATE = """You are a strict critic reviewing application materials before they are sent to a candidate.
Score each piece 0-100 and decide pass/fail (pass requires score >= 70) against this rubric:
- Relevance: directly addresses the job analysis and match report
- Specificity: concrete details, not generic boilerplate
- Tone: professional and confident
- Grounding: makes no claims about the candidate beyond what the match report supports — reject any
  fabricated experience, skills, or achievements

Job analysis:
{job_analysis}

Match report:
{match_report}

Cover letter:
{cover_letter}

Interview prep:
{interview_prep}

For each of cover_letter and interview_prep, give a score, a pass/fail (pass = score >= 70), and specific,
actionable feedback on what to fix if it fails.
"""


def critique(
    job_analysis: dict, match_report: dict, cover_letter: dict, interview_prep: dict
) -> CriticFeedback:
    prompt = PROMPT_TEMPLATE.format(
        job_analysis=job_analysis,
        match_report=match_report,
        cover_letter=cover_letter,
        interview_prep=interview_prep,
    )
    return generate_structured(prompt, CriticFeedback)
