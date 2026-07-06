"""Provider-agnostic structured LLM calls. Currently backed by Gemini;
swap the implementation here to change providers without touching agent code."""

import time
from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import settings

MODEL_NAME = "gemini-2.5-flash"

# Free-tier Gemini returns transient 503s under load fairly often; a short
# retry with backoff clears most of them without the caller needing to know.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

T = TypeVar("T", bound=BaseModel)


@lru_cache
def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def generate_structured(prompt: str, schema: type[T]) -> T:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _get_client().models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return response.parsed
        except errors.ServerError:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
