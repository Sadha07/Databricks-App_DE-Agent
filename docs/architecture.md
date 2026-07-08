# Architecture

## Layered design

Three cleanly separated layers so the agent logic never depends on Streamlit and
Streamlit holds no business logic.

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Presentation | `de_agent.ui` | Streamlit 3-pane app — renders graph state, captures approvals, streams progress |
| Orchestration | `de_agent.agent` | LangGraph graph, nodes, edges, `interrupt()` HITL gates, checkpointer |
| Capabilities | `de_agent.services` | Databricks SDK, LLM providers, profiling, validation, artifacts |
| Domain | `de_agent.domain` | Pure pydantic models, no I/O |

## Principles

1. **The graph is the source of truth.** The UI reads state and resumes it; it
   never runs pipeline logic.
2. **Every side effect goes through a service interface.** Nodes depend on
   Protocols (`DatabricksService`, `LLMClient`), resolved from the `AppContainer`
   injected into `config["configurable"]`. Real and fake implementations are
   interchangeable.
3. **HITL via `interrupt()`.** Dynamic interrupts pause the graph; the Postgres
   checkpointer persists; the UI resumes with `Command(resume=...)`.
4. **Typed config.** All configuration flows through `pydantic-settings`.
5. **Bounded retries.** Every self-correction loop is capped by `max_retries`.

## Flow

```
clarification → environment_setup → profiling → planning
  → bronze → silver → gold_reasoning → gold_planning → gold_build → finalize
```

Interrupt points: clarification (when info is missing), SQL approval (before each
layer executes, when `REQUIRE_APPROVAL=true`), and Gold confirmation.

## Build loop (Bronze / Silver / Gold)

`agent/nodes/notebook_generation.py::build_layer` is shared by all three layers:

1. Generate SQL from the layer spec + profile.
2. (optional) Approval gate via `interrupt()` — placed **before** execution so a
   resume never re-runs SQL.
3. Execute; on failure feed the error back to the LLM and retry (≤ `max_retries`).
4. Validate output; on failure feed validation back and retry.
5. Persist the notebook and advance.

## Local vs. Databricks

`AppContainer` picks implementations from settings:

- `DE_AGENT_ENV=local` (no Databricks host) → `InMemoryDatabricksService` +
  optional `FakeLLMClient`. The full graph runs with zero cloud access.
- `DE_AGENT_ENV=databricks` → `SdkDatabricksService` + Databricks/Groq LLM, Postgres
  checkpointer.

## Testing

- Unit: services + nodes with fabricated state and the deterministic fake LLM.
- Integration: the whole graph with fakes and `MemorySaver`, including an
  interrupt/resume path and a forced SQL-error recovery.
