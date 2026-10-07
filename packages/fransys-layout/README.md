# fransys-layout

The layout engines of Fransys. **Internal: Fransys is the only consumer.** It is a package of this uv workspace. Do not depend on it directly; there are no stability promises.

Status: WP1 to WP14 are done (geometry, stages, both lints, the schematic engine: `lay_out_schematic` reads a model, lays it out and returns it with derived `layout.*` records, and the end-to-end use cases with their goldens). Ladder discovery (WP15, WP16), branch junctions and the marker box (WP18), drawing text (WP17) and persisted cross-reference partners (WP19) are done too: WP1 to WP19 are done. Since then: marker padding (render spec D8) and the board black box (`docs/archive/specs/2026-09-23-board-black-box.md`: a cabinet page draws a board's connectors only, designations `-A1-X1`). The layout deep dive (`docs/archive/specs/2026-09-24-layout-deep-dive.md`, merged 2026-09-25) replaced ladder discovery with chain discovery and stacked columns from the top; its rulings live in the package's design notes. CT5 added the second engine, the cable engine (layout-0141). The package roadmap is closed (decision layout-0118). Open layout work is on the project roadmap.

## What it is

A set of passes on the [fransys-model](../../packages/fransys-model) `Model`. An author connects components, places them in the `=` and `+` aspect trees, and may add soft hints. An engine decides drawing sets, pages, symbol positions, wire routes, cross-page links and label positions, and returns a new `Model` that carries the result as derived `layout.*` records.

```python
def lay_out_schematic(model: Model) -> tuple[Model, tuple[Finding, ...]]
def lay_out_cables(model: Model) -> tuple[Model, tuple[Finding, ...]]
```

```
Model (core, facet, authored layout.*)
   │
   ▼  read
 resolve ─► columns ─► partition ─► place ─► labels.place_slot_labels ─► links ─► route
                                        ─► labels.place_wire_labels ─► lint
   │
   ▼  write
Model (… plus derived layout.*)  +  findings
```

`lay_out_cables` lays out one block per reading and subject: two rows of end boxes, the closed cable box between them, and one wire per core (layout-0141). The rows are a two-colouring of the block's ends (model-0164). Between the cable box and the bottom row, a channel holds the wires that bend (layout-0145). A harness is one block, its cable boxes inside one dashed box (layout-0146). A cable it cannot draw whole gets no block. `fransys_pdf` then stops any export that asks for that block (pdf-0022). The two engines replace only their own record kinds, so they run in either order.

The model is the hub. This package reads the model and writes the model. It renders nothing, reads no file and defines no record kind: every `layout.*` kind lives in `fransys_model.layout`.

## The shape

| Layer | Holds |
|---|---|
| `geometry/` | Integer grid units, boxes, the symbol-library adapter, text metrics. The only place a `float` or a symbol library appears |
| `stages/` | Resolve, chains, columns, partition, place, route, links, labels. Pure functions over small frozen values. They know the model kernel, not the vocabulary |
| `lint/` | The QA gate: geometric checks, and a separate connectivity coherence check |
| `engines/` | `schematic/` and `cable/`. The only code that reads and writes model records |

A rung written in a front end lowers to ordinary connectivity plus a `layout.chain` hint. Circuits written net by net have no chain and get their columns from discovery. Both feed the same stages.

## Rules that define it

- An engine is a pure pass. No I/O, no clock, no randomness.
- Hints, not pins: no authored record holds a coordinate or a page number.
- A wire endpoint is an `Id[Port]`. Nothing is looked up by designation, tag or label.
- Connectivity is checked apart from geometry. A lint score is a report, never an optimiser objective.
- Same model in, same `digests["layout"]` out, whatever the authoring order. Adding one device moves placements only on its group's pages.
- Integers above the symbol adapter. Coordinates are grid units, G = M/8 = 0.3125 mm.
- Layout problems are `Finding`s, so a half-finished design still draws. Structural problems raise. Nothing is shrunk or scaled to fit.
- A run replaces every derived `layout.*` record of its own engine's kinds. It never patches.

## Dependencies and prerequisites

Runtime dependencies are `fransys-model` and `electrical-symbols`, both workspace members, and `graphical-symbols`, pinned by an exact git tag to its own repository (root decision 0015). No solver and no graph library. Python 3.15, because the model needs the builtin `frozendict`.

Every outside prerequisite of WP1 to WP19 is met. The list is in the archived roadmap.

## Develop

Requires [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/). Run from the repo root, where `just ci` gates the whole workspace.

```bash
uv sync
just ci
uv run pytest packages/fransys-layout   # this package's tests alone
```
