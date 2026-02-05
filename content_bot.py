"""Content automation tool for Evolvra.

Run instructions:
1) Install dependencies: pip install -r requirements.txt
2) Set OPENAI_API_KEY in your environment.
3) Generate a single article:
   python content_bot.py --topic "..." --audience "..." --platform linkedin --words 1200 --tone "smart, friendly, practical"
4) Generate a calendar batch:
   python content_bot.py --calendar weekly --count 4
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jsonschema import validate

from topics import generate_topics
from utils import META_SCHEMA, ensure_dir, get_output_dir, slugify, write_json, write_text
from writer import ContentWriter, validate_meta


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_outputs(base_dir: Path, article: str, social: str, meta: Dict[str, Any]) -> None:
    ensure_dir(base_dir)
    write_text(base_dir / "article.md", article)
    write_text(base_dir / "social.md", social)
    write_json(base_dir / "meta.json", meta)


def validate_meta_schema(meta: Dict[str, Any]) -> None:
    validate(instance=meta, schema=META_SCHEMA)


def run_single(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    writer = ContentWriter(args.config)
    payload = writer.generate_package(
        topic=args.topic,
        audience=args.audience,
        platform=args.platform,
        words=args.words,
        tone=args.tone,
    )
    slug = slugify(args.topic)
    payload["meta"]["slug"] = slug
    payload["meta"]["date"] = date.today().isoformat()
    meta_errors = validate_meta(payload["meta"])
    if meta_errors:
        raise ValueError(f"Meta validation failed: {meta_errors}")
    validate_meta_schema(payload["meta"])
    output_dir = get_output_dir("outputs", topic=args.topic)
    write_outputs(output_dir, payload["article"], payload["social"], payload["meta"])


def run_calendar(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    writer = ContentWriter(args.config)
    pillars = config["content"]["pillars"]
    topics = generate_topics(
        pillars=pillars,
        count=args.count,
        model=config["generation"]["model"],
        temperature=config["generation"]["temperature"],
    )
    for item in topics:
        topic = item.get("title", "Untitled topic")
        payload = writer.generate_package(
            topic=topic,
            audience=args.audience,
            platform=args.platform,
            words=args.words,
            tone=args.tone,
        )
        slug = slugify(topic)
        payload["meta"]["slug"] = slug
        payload["meta"]["date"] = date.today().isoformat()
        meta_errors = validate_meta(payload["meta"])
        if meta_errors:
            raise ValueError(f"Meta validation failed: {meta_errors}")
        validate_meta_schema(payload["meta"])
        output_dir = get_output_dir("outputs", topic=topic)
        write_outputs(output_dir, payload["article"], payload["social"], payload["meta"])


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evolvra content automation tool")
    parser.add_argument("--topic", help="Article topic")
    parser.add_argument("--audience", default="Business owners and marketing leads")
    parser.add_argument("--platform", default="linkedin")
    parser.add_argument("--words", type=int, default=1200)
    parser.add_argument("--tone", default="smart, friendly, practical")
    parser.add_argument("--calendar", choices=["weekly", "monthly"], help="Generate a content calendar")
    parser.add_argument("--count", type=int, default=4, help="Number of articles to generate")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    if not config:
        print("Config not found or empty.")
        return 1
    if not args.topic and not args.calendar:
        print("Provide --topic or --calendar.")
        return 1
    if not (Path(args.config).exists()):
        print("Config file missing.")
        return 1
    if "OPENAI_API_KEY" not in os.environ:
        print("Missing OPENAI_API_KEY environment variable.")
        return 1
    if args.topic:
        run_single(args, config)
    if args.calendar:
        run_calendar(args, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
