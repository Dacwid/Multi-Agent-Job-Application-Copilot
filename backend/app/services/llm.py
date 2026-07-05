"""Provider-agnostic structured LLM calls. Currently backed by Gemini;
swap the implementation here to change providers without touching agent code."""

from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings

MODEL_NAME = "gemini-3.5-flash"

T = TypeVar("T", bound=BaseModel)


@lru_cache
def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def generate_structured(prompt: str, schema: type[T]) -> T:
    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return response.parsed
