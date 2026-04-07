"""Optional OpenAI summarization for logs (assistive only; not used for classification)."""

from __future__ import annotations

import os
from typing import Any


def summarize_log(log_text: str, max_chars: int = 4000) -> str | None:
    """
    Return a short summary if OPENAI_API_KEY is set; otherwise None.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=key)
    snippet = log_text[:max_chars]
    resp: Any = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": "Summarize CI failure logs in 2-4 bullet points. Be concrete.",
            },
            {"role": "user", "content": snippet},
        ],
        temperature=0.2,
    )
    choice = resp.choices[0]
    return choice.message.content if choice and choice.message else None
