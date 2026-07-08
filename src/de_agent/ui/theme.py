"""Small presentation helpers shared across UI components."""

from __future__ import annotations

from de_agent.agent.state import StageStatus

_STATUS_ICON = {
    StageStatus.PENDING.value: "⚪",
    StageStatus.IN_PROGRESS.value: "🔵",
    StageStatus.IN_REVIEW.value: "🟡",
    StageStatus.DONE.value: "🟢",
    StageStatus.FAILED.value: "🔴",
}


def status_icon(status: str) -> str:
    return _STATUS_ICON.get(status, "⚪")
