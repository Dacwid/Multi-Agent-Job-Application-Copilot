from langgraph.graph import END, START, StateGraph

from app.agents.cover_letter import draft_cover_letter
from app.agents.interview_prep import prepare_interview
from app.agents.job_analyst import analyze_job_posting
from app.agents.resume_matcher import match_resume
from app.agents.run_logging import run_agent
from app.agents.state import AppState


def _job_analyst_node(state: AppState) -> dict:
    result = run_agent(
        state["application_id"],
        "job_analyst",
        "job_analysis",
        lambda: analyze_job_posting(state["job_posting"]),
    )
    return {"job_analysis": result.model_dump()}


def _resume_matcher_node(state: AppState) -> dict:
    result = run_agent(
        state["application_id"],
        "resume_matcher",
        "match_report",
        lambda: match_resume(state["job_analysis"], state["resume_text"]),
    )
    return {"match_report": result.model_dump()}


def _cover_letter_node(state: AppState) -> dict:
    result = run_agent(
        state["application_id"],
        "cover_letter",
        "cover_letter",
        lambda: draft_cover_letter(state["job_analysis"], state["match_report"]),
    )
    return {"cover_letter": result.model_dump()}


def _interview_prep_node(state: AppState) -> dict:
    result = run_agent(
        state["application_id"],
        "interview_prep",
        "interview_prep",
        lambda: prepare_interview(state["job_analysis"], state["match_report"]),
    )
    return {"interview_prep": result.model_dump()}


def _build_graph():
    builder = StateGraph(AppState)
    builder.add_node("job_analyst", _job_analyst_node)
    builder.add_node("resume_matcher", _resume_matcher_node)
    builder.add_node("cover_letter", _cover_letter_node)
    builder.add_node("interview_prep", _interview_prep_node)

    builder.add_edge(START, "job_analyst")
    builder.add_edge("job_analyst", "resume_matcher")
    builder.add_edge("resume_matcher", "cover_letter")
    builder.add_edge("resume_matcher", "interview_prep")
    builder.add_edge("cover_letter", END)
    builder.add_edge("interview_prep", END)

    return builder.compile()


graph = _build_graph()
