# Databricks Medallion Agent

An autonomous data engineering agent that builds a full **Bronze → Silver → Gold**
Medallion architecture in Databricks Unity Catalog from a raw dataset, with
human-in-the-loop review and self-correcting SQL generation. Orchestrated with
**LangGraph**, served as a **Streamlit** app on **Databricks Apps**.

## Architecture

Three cleanly separated layers:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Presentation | `de_agent.ui` | Streamlit 3-pane app — renders graph state, captures approvals, streams progress |
| Orchestration | `de_agent.agent` | LangGraph graph, nodes, edges, `interrupt()` HITL gates, checkpointer |
| Capabilities | `de_agent.services` | Databricks SDK, LLM providers, profiling, validation, artifacts |

See [docs/architecture.md](docs/architecture.md) for the full design.

## Quickstart (local)

```bash
uv sync --extra dev          # install
cp .env.example .env         # configure (set LLM_PROVIDER=fake to run with no keys)
make run                     # launch Streamlit at http://localhost:8501
```

Run the whole thing with **no cloud dependencies** by setting `DE_AGENT_ENV=local`
and `LLM_PROVIDER=fake` — the app wires in-memory fakes for Databricks and the LLM
so you can exercise the full graph, HITL gates, and retries with the bundled dummy
dataset.

## Common commands

```bash
make lint     # ruff
make type     # mypy (strict on src/)
make test     # pytest (unit + integration)
make run      # streamlit
```

## Deploy to Databricks Apps

```bash
make export-reqs             # sync requirements.txt from the lock
databricks bundle deploy -t dev
```

The app runs as a **service principal**; grant it Unity Catalog privileges on the
target catalog (`TARGET_CATALOG`). See [docs/runbook.md](docs/runbook.md).
