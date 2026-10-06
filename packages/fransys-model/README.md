# fransys-model

The backend data structure of Fransys. **Internal: Fransys is the only consumer.** It is a package of this workspace and may be merged into `fransys` as `fransys.model`. Do not depend on it directly; there are no stability promises.

Status: implemented and absorbed into the workspace (root decision 0010). The kernel, vocabulary, derive layer and layout records are in place and covered by tests; further work is on the project roadmap.

## What it is

One strict, immutable model of an electrical system, built on Python 3.15's builtin `frozendict`. Every Fransys input writes into it. Every output (schematic pages, cable drawings, terminal lists, PLC lists, BOMs, wire labels, KiCad netlists) is a pure function of it.

```
inputs ──► Draft ── freeze() ──► Model ──► passes (allocate, number, lay out) ──► derive ──► outputs
               (mutable)             (immutable, validated, content-hashed)
```

The model is the hub: an input writes a `Draft`, a pass is `Model -> Model`, an output reads a `Model`, and nothing bypasses it. Engineering records store what exists and how it is connected, and nothing about how it is drawn. Layout hints and layout results live in their own `layout.*` namespace, which engineering records can never reference (decision 0009).

## The shape

```python
model.tables["item"][item_id]        # kind -> id -> record, frozendict all the way
```

| Layer | Holds |
|---|---|
| `kernel/` | Records, typed ids, `Draft` → `freeze()` → `Model`, canonical JSON and digest, merge, diff. Knows no engineering |
| `vocab/` | A closed set of core kinds: `Part`, `FunctionTemplate`, `PortTemplate`, `InternalLink`, `Item`, `Function`, `Port`, `Net`, `Conductor`, `Mate`, `AspectNode`, `Placement`, `Project`. Plus open typed facets (terminal, PLC, cable, connector, PCB) and validators |
| `layout/` | The `layout.*` record kinds: authored hints and rule parameters, derived drawing sets, pages, placements, routes, link markers and labels. The engines that write them live in `fransys-layout`, not here |
| `derive/` | Indexes, net closure, numbering and PLC-allocation passes, and the queries and report rows Fransys formats |

A relay is one `Item` with several `Function`s, so its coil and contacts can sit on different pages without any tag-reuse mechanism. A wire is one `Conductor`. An MPN lives on one `Part`. A PCB is an `Item` whose components are child items: the same types as a cabinet.

## Rules that define it

- Deeply immutable after `freeze()`; the closed value-type set bans `float`, `list`, `dict`.
- References are typed `Id[K]` values, never strings. Designations (`-K1`, `X03:4`) are rendered, never parsed.
- Ids derive from a stable authoring key (`uuid5`), not from auto-numbered designations or declaration order.
- Merging never overwrites: an id clash with different content is an error.
- Structural errors raise at `freeze()` and name the authoring source. Engineering problems are returned as `Finding`s.

## Develop

Requires [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/). Run from the repo root, where `just ci` gates the whole workspace.

```bash
uv sync
just ci
uv run pytest packages/fransys-model   # this package's tests alone
```
