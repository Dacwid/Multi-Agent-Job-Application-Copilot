from langgraph.graph import END, START, StateGraph

from app.agents.cover_letter import draft_cover_letter
from app.agents.critic import critique
from app.agents.interview_prep import prepare_interview
from app.agents.job_analyst import analyze_job_posting
from app.agents.resume_matcher import match_resume
from app.agents.run_logging import run_agent
from app.agents.state import AppState

# Initial draft + at most this many revision rounds before accepting the best effort.
MAX_CRITIC_ROUNDS = 3


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
    attempt = state.get("revision_count", 0) + 1
    critic_feedback = state.get("critic_feedback")
    feedback = critic_feedback["cover_letter_feedback"] if critic_feedback else None
    result = run_agent(
        state["application_id"],
        "cover_letter",
        "cover_letter",
        lambda: draft_cover_letter(state["job_analysis"], state["match_report"], feedback),
        attempt=attempt,
    )
    return {"cover_letter": result.model_dump()}


def _interview_prep_node(state: AppState) -> dict:
    attempt = state.get("revision_count", 0) + 1
    critic_feedback = state.get("critic_feedback")
    feedback = critic_feedback["interview_prep_feedback"] if critic_feedback else None
    result = run_agent(
        state["application_id"],
        "interview_prep",
        "interview_prep",
        lambda: prepare_interview(state["job_analysis"], state["match_report"], feedback),
        attempt=attempt,
    )
    return {"interview_prep": result.model_dump()}


def _critic_node(state: AppState) -> dict:
    attempt = state.get("revision_count", 0) + 1
    result = run_agent(
        state["application_id"],
        "critic",
        None,
        lambda: critique(
            state["job_analysis"],
            state["match_report"],
            state["cover_letter"],
            state["interview_prep"],
        ),
        attempt=attempt,
    )
    return {"critic_feedback": result.model_dump(), "revision_count": attempt}


def _route_after_critic(state: AppState) -> str | list[str]:
    feedback = state["critic_feedback"]
    both_pass = feedback["cover_letter_pass"] and feedback["interview_prep_pass"]
    if both_pass or state["revision_count"] >= MAX_CRITIC_ROUNDS:
        return END

    targets = []
    if not feedback["cover_letter_pass"]:
        targets.append("cover_letter")
    if not feedback["interview_prep_pass"]:
        targets.append("interview_prep")
    return targets


def _build_graph():
    builder = StateGraph(AppState)
    builder.add_node("job_analyst", _job_analyst_node)
    builder.add_node("resume_matcher", _resume_matcher_node)
    builder.add_node("cover_letter", _cover_letter_node)
    builder.add_node("interview_prep", _interview_prep_node)
    builder.add_node("critic", _critic_node)

    builder.add_edge(START, "job_analyst")
    builder.add_edge("job_analyst", "resume_matcher")
    builder.add_edge("resume_matcher", "cover_letter")
    builder.add_edge("resume_matcher", "interview_prep")
    builder.add_edge("cover_letter", "critic")
    builder.add_edge("interview_prep", "critic")
    builder.add_conditional_edges("critic", _route_after_critic)

    return builder.compile()


graph = _build_graph()
