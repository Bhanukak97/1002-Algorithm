"""OpenAI-powered writer for Evolvra content."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml
from openai import OpenAI

from utils import META_SCHEMA

REQUIRED_HEADINGS = ["# ", "## Hook", "## Context", "## What to do next", "## Conclusion"]


@dataclass
class GenerationConfig:
    model: str
    max_output_tokens: int
    temperature: float


class ContentWriter:
    """Generate long-form articles and social snippets."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config = self._load_config(config_path)
        self.generation = GenerationConfig(**self.config["generation"])
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def _load_config(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _request_completion(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.generation.model,
            input=prompt,
            temperature=self.generation.temperature,
            max_output_tokens=self.generation.max_output_tokens,
        )
        return response.output_text.strip()

    def generate_outline(self, topic: str, audience: str, platform: str, words: int, tone: str) -> str:
        """Generate an outline with key points and examples."""
        config = self.config
        prompt = f"""
You are an expert content strategist writing for {config['company']['name']}. Create a detailed outline.

Topic: {topic}
Audience: {audience}
Platform: {platform}
Target length: {words} words
Tone: {tone}

Company description: {config['company']['description']}
Author bio: {config['author']['bio']}
Tone rules: {config['style']['tone_rules']}
Banned phrases: {', '.join(config['style']['banned_phrases'])}

Requirements:
- Provide a structured outline with headings and subheadings.
- Include 3-5 section headings with subheadings.
- Include specific examples but do not invent client names or results.
- Add one mini-case or scenario relevant to Evolvra clients.
- Add a checklist titled "What to do next" with 5 bullet items.
- Provide 5 SEO keywords and a meta description of 155-160 characters.
- Provide 3 social snippets (LinkedIn, Facebook, Instagram caption) with CTA.
- Avoid em dashes.
Return the outline in Markdown.
"""
        return self._request_completion(prompt)

    def generate_article(self, outline: str, topic: str, audience: str, platform: str, words: int, tone: str) -> str:
        """Expand outline into a full article."""
        config = self.config
        prompt = f"""
You are an expert writer for {config['company']['name']}. Expand the outline into a full article.

Topic: {topic}
Audience: {audience}
Platform: {platform}
Target length: {words} words
Tone: {tone}

Company description: {config['company']['description']}
Author bio: {config['author']['bio']}
Tone rules: {config['style']['tone_rules']}
Banned phrases: {', '.join(config['style']['banned_phrases'])}

Outline:
{outline}

Article requirements:
- Must include Hook, Context, 3-5 sections with subheadings, examples, a mini-case scenario, a "What to do next" checklist, and a short Conclusion.
- Provide SEO keywords and meta description near the end in a clearly labeled section.
- Provide 3 social snippets at the end in a clearly labeled section.
- Avoid em dashes.
- Never invent client names or results. Use hypotheses or best practices.
- Avoid statistics unless provided in the outline.
Return the full article in Markdown.
"""
        return self._request_completion(prompt)

    def _extract_meta(self, article_markdown: str) -> Tuple[List[str], str]:
        keyword_match = re.search(r"SEO Keywords:\s*(.+)", article_markdown)
        description_match = re.search(r"Meta Description:\s*(.+)", article_markdown)
        keywords: List[str] = []
        if keyword_match:
            raw = keyword_match.group(1)
            keywords = [item.strip() for item in re.split(r"[,;]", raw) if item.strip()]
        description = description_match.group(1).strip() if description_match else ""
        return keywords[:5], description

    def _extract_social(self, article_markdown: str) -> str:
        social_match = re.search(r"Social Snippets:\s*(.*)", article_markdown, re.DOTALL)
        return social_match.group(1).strip() if social_match else ""

    def self_check(self, article_markdown: str) -> List[str]:
        """Validate article content against requirements."""
        errors: List[str] = []
        if "—" in article_markdown:
            errors.append("Contains em dash.")
        for heading in REQUIRED_HEADINGS:
            if heading not in article_markdown:
                errors.append(f"Missing heading: {heading}")
        if article_markdown.count("## ") < 6:
            errors.append("Not enough section headings.")
        if "- [ ]" not in article_markdown and "- " not in article_markdown:
            errors.append("Checklist missing.")
        fake_claim = re.search(r"\b(we|our team|evolvra)\b.*\b(achieved|increased|grew|boosted)\b.*\d+%", article_markdown, re.IGNORECASE)
        if fake_claim:
            errors.append("Potential fabricated percentage claim.")
        return errors

    def revise_article(self, article_markdown: str, errors: List[str]) -> str:
        """Revise article once based on validation errors."""
        prompt = f"""
Revise the following article to fix these issues:
{json.dumps(errors, indent=2)}

Rules:
- Keep the required structure and headings.
- Remove em dashes.
- Remove any fabricated claims.
- Preserve the SEO keywords and meta description if they are valid.
- Return only the revised Markdown article.

Article:
{article_markdown}
"""
        return self._request_completion(prompt)

    def generate_package(
        self,
        topic: str,
        audience: str,
        platform: str,
        words: int,
        tone: str,
    ) -> Dict[str, Any]:
        """Generate article, social snippets, and metadata."""
        outline = self.generate_outline(topic, audience, platform, words, tone)
        article = self.generate_article(outline, topic, audience, platform, words, tone)
        errors = self.self_check(article)
        if errors:
            article = self.revise_article(article, errors)
        keywords, description = self._extract_meta(article)
        social = self._extract_social(article)
        return {
            "article": article,
            "social": social,
            "meta": {
                "title": topic,
                "keywords": keywords or ["content systems", "AI automation", "digital marketing", "CRM workflows", "operations"],
                "description": description,
                "platform": platform,
                "slug": "",
            },
        }


def validate_article_structure(article_markdown: str) -> List[str]:
    """Standalone validator for tests."""
    writer = ContentWriter.__new__(ContentWriter)
    return ContentWriter.self_check(writer, article_markdown)


def validate_meta(meta: Dict[str, Any]) -> List[str]:
    """Validate meta payload against schema."""
    errors: List[str] = []
    if len(meta.get("keywords", [])) != 5:
        errors.append("Keywords must include 5 items.")
    if not (155 <= len(meta.get("description", "")) <= 160):
        errors.append("Description must be 155-160 characters.")
    if not meta.get("title"):
        errors.append("Title missing.")
    return errors
