# fransys-layout

The layout of Fransys: the cable, diagram and overview engines, the core, the symdef layer and the Drawing value. **Internal: Fransys is the only consumer.** It is a package of this uv workspace. Do not depend on it directly; there are no stability promises.

Status: the schematic engine and its `stages/` are deleted (DEL-12). The engines left are cable (layout-0141), diagram and overview, with the core (`fransys_layout.core`), the symdef layer (`fransys_layout.symbols`) and the Drawing value (`fransys_layout.drawing`). The package roadmap is closed (decision layout-0118). Open layout work is on the project roadmap.

## What it is

A set of passes on the [fransys-model](../../packages/fransys-model) `Model`. An author connects components, places them in the `=` and `+` aspect trees, and may add soft hints. An engine decides blocks, sheets, symbol positions and wire routes, and returns a new `Model` that carries the result as derived `layout.*` records.

```python
def lay_out_cables(model: Model) -> tuple[Model, tuple[Finding, ...]]
```


`lay_out_cables` lays out one block per reading and subject: two rows of end boxes, the closed cable box between them, and one wire per core (layout-0141). The rows are a two-colouring of the block's ends (model-0164). Between the cable box and the bottom row, a channel holds the wires that bend (layout-0145). A harness is one block, its cable boxes inside one dashed box (layout-0146). A cable it cannot draw whole gets no block. `fransys_pdf` then stops any export that asks for that block (pdf-0022). Each engine replaces only its own record kinds, so they run in any order.

`options` carries the text placement table (decision layout-0192): this package holds no drawing convention of its own for it, and `fransys_el` supplies the electrical one.

The model is the hub. This package reads the model and writes the model. It renders nothing, reads no file and defines no record kind: every `layout.*` kind lives in `fransys_model.layout`.

## The shape

| Layer | Holds |
|---|---|
| `geometry/` | Integer grid units, boxes, runs, cell index, grid paths, the symbol-library adapter, text metrics. The only place a `float` or a symbol library appears |
| `lint/` | The diagram check and the finding codes |
| `engines/` | `cable/`, `diagram/` and `overview/`. The only code that reads and writes model records |

## Rules that define it

- An engine is a pure pass. No I/O, no clock, no randomness.
- Hints, not pins: no authored record holds a coordinate or a page number.
- A wire endpoint is an `Id[Port]`. Nothing is looked up by designation, tag or label.
- A lint score is a report, never an optimiser objective.
- Same model in, same `digests["layout"]` out, whatever the authoring order. Adding one device moves placements only on its group's pages.
- Integers above the symbol adapter. Coordinates are grid units, G = M/8 = 0.3125 mm.
- Layout problems are `Finding`s, so a half-finished design still draws. Structural problems raise. Nothing is shrunk or scaled to fit.
- A run replaces every derived `layout.*` record of its own engine's kinds. It never patches.

## Dependencies and prerequisites

Runtime dependencies are `fransys-model` and `electrical-symbols`, both workspace members, and `symdef`, pinned by an exact PyPI version (root decisions 0015 and 0128). No solver and no graph library. Python 3.15, because the model needs the builtin `frozendict`.

Every outside prerequisite of the package's planned work is met. The list is in the archived roadmap.

## Develop

Requires [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/). Run from the repo root, where `just ci` gates the whole workspace.

```bash
uv sync
just ci
uv run pytest packages/fransys-layout   # this package's tests alone
```

- `fransys_layout.drawing`: the `Drawing`, `Sheet` and `Style` values render draws from, stdlib only, JSON by `to_plain` (layout-0315).
