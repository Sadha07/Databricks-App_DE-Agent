"""Environment setup node â€” provision UC scope, upload the dataset, register landing.

Idempotent and permission-aware: if the catalog is missing and creation isn't
allowed, it stops with a clear, actionable error rather than crashing.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

import base64
import re
from typing import Any

from de_agent.agent.nodes._helpers import ai, record_error
from de_agent.agent.state import Layer, StageStatus
from de_agent.config.logging import get_logger
from de_agent.domain.dataset import DatasetRef
from de_agent.services.container import get_container

log = get_logger(__name__)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    return slug or "dataset"


def environment_setup_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    settings = container.settings
    db = container.databricks

    dataset = DatasetRef(**state["dataset"])
    catalog = settings.target_catalog
    schema = _slug(dataset.name)
    volume = "raw"

    cat = db.ensure_catalog(catalog, allow_create=settings.allow_create_catalog)
    if not cat.ok:
        return {
            "errors": record_error(state, node="environment_setup", message=cat.error or "catalog"),
            "layer_status": {**state["layer_status"], Layer.BRONZE.value: StageStatus.FAILED.value},
            "messages": [ai(f"Setup failed: {cat.error}")],
        }

    db.ensure_schema(catalog, schema)
    db.ensure_volume(catalog, schema, volume)

    data = base64.b64decode(state["raw_bytes_b64"])
    volume_path = db.upload_dataset(
        catalog=catalog, schema=schema, volume=volume, filename=dataset.source_filename, data=data
    )

    landing = f"landing_{_slug(dataset.name)}"
    reg = db.register_bronze_table(
        catalog=catalog,
        schema=schema,
        table=landing,
        volume_file_path=volume_path,
        file_format="csv",
    )
    if not reg.ok:
        return {
            "errors": record_error(state, node="environment_setup", message=reg.error or "register"),
            "messages": [ai(f"Landing registration failed: {reg.error}")],
        }

    fq_landing = f"{catalog}.{schema}.{landing}"
    log.info("environment_setup.done", catalog=catalog, schema=schema, landing=fq_landing)
    return {
        "catalog": catalog,
        "schema_name": schema,
        "landing_table": fq_landing,
        "dataset": {**state["dataset"], "volume_path": volume_path},
        "messages": [ai(f"Environment ready. Landing table `{fq_landing}` registered.")],
    }
