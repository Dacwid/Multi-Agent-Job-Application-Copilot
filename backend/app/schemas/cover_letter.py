from pydantic import BaseModel


class CoverLetter(BaseModel):
    body: str
