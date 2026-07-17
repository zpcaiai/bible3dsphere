# Integration dependency graph

Allowed dependency direction:

```text
UI -> Platform API -> Orchestrator -> Safety / Policy / Broker / Arbitration
Broker -> registered read adapter -> source module
Confirmed Command -> registered command adapter -> target module
Source module -> versioned metadata event -> platform consumers
Deletion or consent event -> coordinator -> registered acknowledgements
```

Forbidden dependencies:

- source module directly queries another module's tables;
- recommendation generator calls a command executor without user confirmation;
- Formation Twin creates a habit and habit failure automatically rewrites a
  Twin pattern;
- ordinary workflow overrides Crisis Care;
- service identity bypasses user consent;
- notification or search loads a sensitive source body.

The monolith adapter in `routers/platform_orchestration.py` is the temporary
anti-corruption layer for existing tables. Its functions are private to the
Context Broker path and return allow-listed references, not general row access.
