"""`studykit index <course>`: the id index the pandoc filters resolve references against.

Written to `courses/<c>/_build/index.json` and passed to pandoc as `-M sk-index=<path>`.
The shape is a contract with `pandoc/filters` (refs.lua, mcq.lua, meta.lua):

    {"schema": 1, "course": "<id>", "lang": "de", "title": "…",
     "topics": {"<topic-id>": {"title": "…", "order": 1}},
     "items": {"<id>": {"kind": "exercise|mc|exam-task|summary|overview|cheatsheet",
                        "title": "…", "topic": "<topic-id>|null", "path": "<course-relative>"}},
     "exams": {"<exam-id>": {"title": "…"}},
     "figures": ["<slug>", "topic-map"],
     "sources": {"<doc-id>": {"title": "…", "pages": 40}}}

The index is built best effort: files that do not parse are left out, so pandoc can still
render the rest while `studykit validate` reports the problems.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from studykit.content import CourseTree

INDEX_SCHEMA = 1
ITEM_KINDS = ("exercise", "mc", "exam-task", "summary", "overview", "cheatsheet")


def build(tree: CourseTree) -> dict[str, Any]:
    course = tree.model
    raw = tree.course_doc.data if tree.course_doc else None
    raw = raw if isinstance(raw, dict) else {}

    topics: dict[str, dict[str, Any]] = {}
    if course:
        for order, topic in enumerate(course.topics, start=1):
            topics[topic.id] = {"title": topic.title, "order": order}
    else:
        for order, topic in enumerate(raw.get("topics") or [], start=1):
            if isinstance(topic, dict) and isinstance(topic.get("id"), str):
                topics[topic["id"]] = {
                    "title": str(topic.get("title", topic["id"])),
                    "order": order,
                }

    items: dict[str, dict[str, Any]] = {}
    exams: dict[str, dict[str, Any]] = {}
    for item in tree.items:
        if item.kind == "exam":
            exams.setdefault(item.id, {"title": item.title or item.id})
        elif item.kind in ITEM_KINDS:
            items.setdefault(
                item.id,
                {
                    "kind": item.kind,
                    "title": item.title or item.id,
                    "topic": item.topic if item.topic in topics else None,
                    "path": item.rel,
                },
            )

    return {
        "schema": INDEX_SCHEMA,
        "course": course.id if course else str(raw.get("id") or tree.id),
        "lang": course.lang if course else str(raw.get("lang") or "en"),
        "title": course.title if course else str(raw.get("title") or tree.id),
        "topics": topics,
        "items": items,
        "exams": exams,
        "figures": tree.figure_slugs,
        "sources": tree.sources,
    }


def index_path(tree: CourseTree) -> Path:
    return tree.root / "_build" / "index.json"


def dumps(index: dict[str, Any]) -> str:
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def write(tree: CourseTree) -> tuple[Path, dict[str, Any]]:
    """Write `_build/index.json` (only when it changed) and return its path and content."""
    index = build(tree)
    path = index_path(tree)
    text = dumps(index)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return path, index
