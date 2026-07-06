from app.schemas.cover_letter import CoverLetter
from app.services.llm import generate_structured

PROMPT_TEMPLATE = """Draft a tailored cover letter body for this candidate applying to this role.
Ground every claim about the candidate strictly in the match report below — never fabricate experience.

Job analysis:
{job_analysis}

Match report:
{match_report}
{feedback_section}
Write a concise, specific cover letter body (3-4 paragraphs, no greeting/signature needed).
"""


def draft_cover_letter(
    job_analysis: dict, match_report: dict, feedback: list[str] | None = None
) -> CoverLetter:
    feedback_section = ""
    if feedback:
        feedback_section = (
            "\nA previous draft was rejected for these reasons — address them directly:\n"
            + "\n".join(f"- {item}" for item in feedback)
            + "\n"
        )
    prompt = PROMPT_TEMPLATE.format(
        job_analysis=job_analysis,
        match_report=match_report,
        feedback_section=feedback_section,
    )
    return generate_structured(prompt, CoverLetter)
