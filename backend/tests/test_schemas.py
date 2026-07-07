import pytest
from pydantic import ValidationError

from app.schemas.cover_letter import CoverLetter
from app.schemas.critic_feedback import CriticFeedback
from app.schemas.interview_prep import InterviewPrep
from app.schemas.job_analysis import JobAnalysis
from app.schemas.match_report import MatchReport


def test_job_analysis_accepts_valid_data():
    analysis = JobAnalysis(
        role_title="Senior Backend Engineer",
        seniority="senior",
        required_skills=["Python", "Kafka"],
        nice_to_have_skills=["Go"],
        keywords=["distributed systems"],
        company_signals=["fast-paced"],
        summary="A senior backend role.",
    )
    assert analysis.role_title == "Senior Backend Engineer"


def test_job_analysis_rejects_missing_field():
    with pytest.raises(ValidationError):
        JobAnalysis(
            role_title="Senior Backend Engineer",
            seniority="senior",
            required_skills=["Python"],
            nice_to_have_skills=[],
            keywords=[],
            # missing company_signals and summary
        )


def test_match_report_accepts_valid_data():
    report = MatchReport(
        match_score=75,
        strengths=["Python experience"],
        gaps=["No Kafka experience"],
        suggestions=["Learn Kafka"],
    )
    assert report.match_score == 75


def test_match_report_rejects_wrong_type():
    with pytest.raises(ValidationError):
        MatchReport(
            match_score="not a number",
            strengths=[],
            gaps=[],
            suggestions=[],
        )


def test_cover_letter_accepts_valid_data():
    letter = CoverLetter(body="Dear hiring manager...")
    assert letter.body.startswith("Dear")


def test_cover_letter_rejects_missing_body():
    with pytest.raises(ValidationError):
        CoverLetter()


def test_interview_prep_accepts_valid_data():
    prep = InterviewPrep(
        questions=[
            {"question": "Tell me about yourself", "talking_points": ["Point A"]},
        ]
    )
    assert prep.questions[0].question == "Tell me about yourself"


def test_interview_prep_rejects_malformed_question():
    with pytest.raises(ValidationError):
        InterviewPrep(questions=[{"question": "Missing talking points"}])


def test_critic_feedback_accepts_valid_data():
    feedback = CriticFeedback(
        cover_letter_pass=True,
        cover_letter_score=85,
        cover_letter_feedback=[],
        interview_prep_pass=False,
        interview_prep_score=40,
        interview_prep_feedback=["Too generic"],
    )
    assert feedback.cover_letter_pass is True
    assert feedback.interview_prep_pass is False


def test_critic_feedback_rejects_missing_field():
    with pytest.raises(ValidationError):
        CriticFeedback(
            cover_letter_pass=True,
            cover_letter_score=85,
            cover_letter_feedback=[],
            interview_prep_pass=False,
            # missing interview_prep_score and interview_prep_feedback
        )
