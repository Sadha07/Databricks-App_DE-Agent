"""Checkpointer factory.

Postgres/Lakebase in production (durable, survives app restarts, concurrent-user
safe); an in-memory saver locally. The Databricks Apps filesystem is ephemeral, so
never use a file-based saver there — that is why the default prod path is Postgres.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.base import BaseCheckpointSaver

from de_agent.config.logging import get_logger

if TYPE_CHECKING:
    from de_agent.config.settings import Settings

log = get_logger(__name__)


def create_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    if settings.database_url:
        return _postgres_saver(settings.database_url)
    from langgraph.checkpoint.memory import MemorySaver

    log.warning("checkpointer.memory", detail="no DATABASE_URL set; state is not durable")
    return MemorySaver()


def _postgres_saver(conn_str: str) -> BaseCheckpointSaver:
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(
        conninfo=conn_str,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    saver = PostgresSaver(pool)  # type: ignore[arg-type]
    saver.setup()  # idempotent: creates checkpoint tables if absent
    log.info("checkpointer.postgres", detail="using durable Postgres checkpointer")
    return saver
