# Runbook

## Prerequisites

- Python 3.11+, `uv`, Databricks CLI (`databricks`).
- A SQL warehouse (`DATABRICKS_WAREHOUSE_ID`).
- A Lakebase/Postgres instance for the checkpointer (`DATABASE_URL`).
- The app's **service principal** granted Unity Catalog privileges (see below).

## Unity Catalog privileges

The agent creates catalog/schema/volume/tables. Grant the service principal:

| To do | Grant |
|-------|-------|
| Create catalog (`ALLOW_CREATE_CATALOG=true`) | `CREATE CATALOG` on the metastore |
| Scoped (recommended prod) | Pre-create the catalog; grant `USE CATALOG` + `CREATE SCHEMA` on it |
| Volumes / ingest | `CREATE VOLUME`, `WRITE VOLUME` |
| Tables | `CREATE TABLE` on the schema |

If the catalog is missing and creation is not allowed, `environment_setup` stops
with an actionable message rather than crashing.

## Secrets

Store in a Databricks secret scope and map them in `app.yaml`:

- `de-agent-warehouse-id`
- `de-agent-database-url`
- `de-agent-groq-key` (only if `LLM_PROVIDER=groq`)

## Deploy

```bash
make export-reqs
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

## Rollback

`databricks bundle deploy` is declarative; redeploy a previous git revision to roll
back. Checkpoints in Postgres are keyed by `thread_id` and are unaffected by app
redeploys, so in-flight runs resume after a new deploy.

## Common issues

| Symptom | Likely cause |
|---------|--------------|
| "Catalog does not exist and ALLOW_CREATE_CATALOG is false" | Pre-create the catalog or enable creation |
| State lost after restart | `DATABASE_URL` not set → MemorySaver was used |
| LLM errors on Gold only | Reasoning model too weak — point `*_REASONING` at a stronger model |
