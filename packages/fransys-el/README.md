Fransys electrical conventions: the values the general layout core takes as options.

Role contract: data only. `fransys_el` holds our drawing conventions as frozen option values that `fransys_layout` accepts (`LayoutOptions`); it computes nothing and reads no file. `fransys_layout` and `fransys_render` never import it; the bundle `fransys` passes `fransys_el.OPTIONS` into every layout call (FRANSYS-SPLIT, seam 1).

- `fransys_el.TEXTS`: where each kind of text may stand (rows T1.1 to T1.8, layout-0090): its sides in try-order, the steps along each, and its priority.
- `fransys_el.OPTIONS`: `LayoutOptions(texts=TEXTS)`, the value the bundle passes.
- `fransys_el.TEXT_ROW_IDS`: the row ids T1.1 to T1.8, which the layout design map checks against its rule docs.

Imports: `fransys_model`, `fransys_layout` and `electrical_symbols`, through their top-level surfaces. Decision: `docs/decisions/layout-0192-*.md`.
