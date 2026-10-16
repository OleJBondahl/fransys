Fransys electrical conventions: the values the general layout core takes as options.

Role contract: conventions as values, and the placement-problem builder. `fransys_el` holds our drawing conventions as frozen option values that `fransys_layout` accepts. Its `build(model, kit, conventions)` is a pure function from a model, a symbol kit and conventions to a `PlacementProblem`. It reads facts from `fransys_model.derive`, derives none, and reads no file (el-0002). `fransys_layout` and `fransys_render` never import it; the bundle `fransys` passes `fransys_el.OPTIONS` into every layout call (FRANSYS-SPLIT, seam 1).

- `fransys_el.TEXTS`: where each kind of text may stand (rows T1.1 to T1.8, layout-0090): its sides in try-order, the steps along each, and its priority.
- `fransys_el.OPTIONS`: `LayoutOptions(texts=TEXTS)`, the value the bundle passes.
- `fransys_el.TEXT_ROW_IDS`: the row ids T1.1 to T1.8, which the layout design map checks against its rule docs.
- `fransys_el.build`, `Conventions`, `options`, `SymbolKit`, `Pick`, `Skipped`, `ProblemError`: the builder, its conventions, the symbol kit it takes (one `Pick` per drawn function) and the error for an impossible input (el-0002). `Skipped` names what `build` left out.
- `fransys_el.REF_TINTS`: the eight net-reference fill tints, in link-slot order (el-0001).

Imports: `fransys_model`, `fransys_layout` and `electrical_symbols`, through their top-level surfaces. Decision: `docs/decisions/layout-0192-*.md`.
