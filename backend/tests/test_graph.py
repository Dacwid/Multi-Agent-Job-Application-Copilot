import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents import graph as graph_module
from app.agents import run_logging
from app.schemas.cover_letter import CoverLetter
from app.schemas.critic_feedback import CriticFeedback
from app.schemas.interview_prep import InterviewPrep
from app.schemas.job_analysis import JobAnalysis
from app.schemas.match_report import MatchReport


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def insert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return self

    @property
    def data(self):
        return self._data


class FakeSupabase:
    """Stands in for the real Supabase client so the graph test doesn't
    need network access or credentials — only the chain shapes run_agent
    actually calls are implemented."""

    def table(self, _name):
        return _FakeQuery([{"id": str(uuid.uuid4())}])


def test_graph_runs_to_human_approval_then_approves(monkeypatch):
    monkeypatch.setattr(run_logging, "get_supabase", lambda: FakeSupabase())

    monkeypatch.setattr(
        graph_module,
        "analyze_job_posting",
        lambda posting: JobAnalysis(
            role_title="Backend Engineer",
            seniority="mid",
            required_skills=["Python"],
            nice_to_have_skills=["Go"],
            keywords=["Python"],
            company_signals=["remote-friendly"],
            summary="A backend role.",
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "match_resume",
        lambda job_analysis, resume_text: MatchReport(
            match_score=80,
            strengths=["Python experience"],
            gaps=[],
            suggestions=[],
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "draft_cover_letter",
        lambda job_analysis, match_report, feedback=None: CoverLetter(
            body="A tailored cover letter."
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "prepare_interview",
        lambda job_analysis, match_report, feedback=None: InterviewPrep(
            questions=[{"question": "Tell me about Python", "talking_points": ["Point A"]}]
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "critique",
        lambda job_analysis, match_report, cover_letter, interview_prep: CriticFeedback(
            cover_letter_pass=True,
            cover_letter_score=90,
            cover_letter_feedback=[],
            interview_prep_pass=True,
            interview_prep_score=90,
            interview_prep_feedback=[],
        ),
    )

    graph = graph_module._build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_state = {
        "application_id": "test-app-id",
        "job_posting": "Backend Engineer posting",
        "resume_text": "Python developer resume",
        "job_analysis": None,
        "match_report": None,
        "cover_letter": None,
        "interview_prep": None,
        "critic_feedback": None,
        "revision_count": 0,
        "human_review_started": False,
        "approved": False,
    }

    result = graph.invoke(initial_state, config)

    assert "__interrupt__" in result
    assert result["job_analysis"]["role_title"] == "Backend Engineer"
    assert result["cover_letter"]["body"] == "A tailored cover letter."
    assert result["critic_feedback"]["cover_letter_pass"] is True

    final_result = graph.invoke(Command(resume={"action": "approve"}), config)

    assert "__interrupt__" not in final_result
    assert final_result["approved"] is True
