"""Topic generation for Evolvra content."""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from openai import OpenAI


def generate_topics(pillars: List[str], count: int, model: str, temperature: float) -> List[Dict[str, str]]:
    """Generate ranked topic ideas with angles."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"""
Generate a ranked list of {count} content topic ideas.
Pillars: {', '.join(pillars)}

Return JSON only in this format:
{{
  "topics": [
    {{"title": "...", "angle": "..."}}
  ]
}}
Keep angles short and practical.
Avoid em dashes.
"""
    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=temperature,
        max_output_tokens=600,
    )
    raw = response.output_text.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"{.*}", raw, re.DOTALL)
        if not match:
            return []
        payload = json.loads(match.group(0))
    return payload.get("topics", [])
