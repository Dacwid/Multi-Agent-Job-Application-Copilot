"""Provider-agnostic structured LLM calls. Currently backed by Gemini;
swap the implementation here to change providers without touching agent code."""

from typing import TypeVar

import google.generativeai as genai
from pydantic import BaseModel

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

MODEL_NAME = "gemini-1.5-flash"

T = TypeVar("T", bound=BaseModel)


def generate_structured(prompt: str, schema: type[T]) -> T:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema,
        },
    )
    return schema.model_validate_json(response.text)
