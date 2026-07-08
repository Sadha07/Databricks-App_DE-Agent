"""Shared node utilities: prompt loading, LLM output parsing, message helpers."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def system_for(task: str) -> str:
    """Build a system prompt: a machine-readable TASK marker + the template body.

    The first ``TASK:`` line lets the deterministic fake LLM route responses; real
    models simply read it as context.
    """
    return f"TASK: {task}\n{load_prompt(task)}"


def extract_sql(text: str) -> str:
    match = _SQL_FENCE_RE.search(text)
    sql = match.group(1) if match else text
    return sql.strip().rstrip(";").strip() + ";"


def extract_json(text: str) -> dict[str, Any]:
    match = _JSON_RE.search(text)
    if not match:
        raise ValueError("no JSON object found in LLM output")
    return json.loads(match.group(0))


def ai(text: str) -> AIMessage:
    return AIMessage(content=text)


def record_error(state: dict[str, Any], *, node: str, message: str) -> list[dict[str, Any]]:
    errors = list(state.get("errors", []))
    errors.append({"node": node, "message": message})
    return errors


def bump_retry(state: dict[str, Any], key: str) -> dict[str, int]:
    retries = dict(state.get("retry_count", {}))
    retries[key] = retries.get(key, 0) + 1
    return retries
