from __future__ import annotations

from datetime import date

from jsonschema import validate

from utils import META_SCHEMA, get_output_dir, slugify
from writer import validate_article_structure


def test_slug_and_output_path():
    output = get_output_dir("outputs", topic="My Topic", date_value=date(2024, 1, 2))
    assert output.as_posix().endswith("outputs/2024-01-02/my-topic")
    assert slugify("Hello World!") == "hello-world"


def test_markdown_section_presence():
    article = """
# Title
## Hook
Opening hook.
## Context
Context section.
## Section One
Details.
## Section Two
Details.
## Section Three
Details.
## What to do next
- Do this
- Do that
## Conclusion
Wrap-up.
SEO Keywords: one, two, three, four, five
Meta Description: """ + "x" * 155 + """
Social Snippets:
LinkedIn: ...
"""
    errors = validate_article_structure(article)
    assert not errors


def test_meta_schema_validity():
    meta = {
        "title": "Test",
        "keywords": ["one", "two", "three", "four", "five"],
        "description": "x" * 155,
        "platform": "linkedin",
        "date": "2024-01-02",
        "slug": "test",
    }
    validate(instance=meta, schema=META_SCHEMA)
