from pydantic import BaseModel


class MatchReport(BaseModel):
    match_score: int
    strengths: list[str]
    gaps: list[str]
    suggestions: list[str]
