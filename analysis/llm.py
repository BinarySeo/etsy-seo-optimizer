"""
llm.py
------
Shared OpenAI access for the analysis modules.

The client is created on first use rather than at import time, so the dashboard and the
non-AI analysis steps still run when OPENAI_API_KEY isn't set (e.g. mock-data mode, CI).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"


class LLMUnavailableError(RuntimeError):
    """Raised when an AI feature is used without an OpenAI API key configured."""


def llm_available() -> bool:
    """True when an OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def get_model() -> str:
    """Model name, overridable with OPENAI_MODEL in .env."""
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


@lru_cache(maxsize=1)
def get_client():
    """Return a shared OpenAI client (retries transient errors, 60s timeout)."""
    if not llm_available():
        raise LLMUnavailableError(
            "OPENAI_API_KEY is not set. Add it to .env to enable AI briefings and insights."
        )
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=3, timeout=60)


def complete(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """
    Send one user prompt and return the text of the reply.
    json_mode=True asks the API to return a single valid JSON object.
    """
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = get_client().chat.completions.create(
        model=get_model(),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content or ""
