Fransys output: laid-out model to SVG pages and cable blocks.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

`pages(model) -> frozendict[str, str]` renders every `layout.page` of a laid-out model to one
SVG each, keyed by `render_id(page.id)`: unit outlines (decision layout-0045: one dash-dot
outline, labelled `<unit title> rev <revision>`, per black-box unit instance on the page), symbols (real library symbols and
the generic box, drawn through `graphical_symbols.to_fragment`; a truly unknown key gets an 8x8
G placeholder), routes, D8's junction dots, D8's link markers, and D7's label text, in that fixed
order; a bound lead (`Line.port`) draws only when its port has a route, marker or marking label
on it (decision render-0002). The
SVG carries schematic content only -- no frame, grid or title block (`fransys_pdf` draws
those, once, on every page). `check(model) -> tuple[Finding, ...]` reports `UNKNOWN_SYMBOL_KEY`,
`LIBRARY_VERSION_MISMATCH` and `LAYOUT_MISSING`; `PIN_MAP_INCOMPLETE` moved into
`fransys_layout` (decision layout-0041, the binding it needs lives there). This package
imports `fransys_model`, `graphical_symbols` and `electrical_symbols` only, never
`fransys_layout`.

`cable_blocks(model) -> frozendict[str, str]` renders every `layout.cable_block` to one SVG, keyed `cable_block_key(unit, subject)` (render-0007). It draws only what the block's records hold, and every text is a `derive.cable_drawing` function's. A core is two runs that stop at the closed cable box. A harness block's dashed box surrounds its cable boxes and carries the harness's `printed_designation`. A by-others end box is dashed, its edges and dividers in one phase.

`diagram_sheets(model) -> frozendict[str, str]` renders every `layout.diagram_sheet` to one full-sheet SVG (594 x 420 mm), keyed `render_id(sheet.id)` (render-0009). Boxes, tabs, lines and cut markers come from the records; every text is a `derive.block_diagram` function's. It draws no frame, grid or title block.

Status: work package `render` complete (PARTS 1-7, including PART 5b's `LAYOUT_MISSING` fix and
PART 7's D7 font-size fix), wired into the facade (`fransys.pipeline`). Does not merge on
green CI alone: the owner looks at the rendered pages and the complete demo cabinet PDF first
(spec acceptance, the second of his two looks).
See `docs/decisions/render-0001-junction-rule-constants-and-open-choices.md` for the junction
rule, this package's own constants and their sources, and the choices made along the way. The
link-marker glyph draws the record's own `width`/`height` (model-0037, layout-0043, the "marker
box" work package's PART B): its box is no longer a render-side constant. CT5 added `cable_blocks` (render-0007).

## Rules moved from docstrings (docstring sweep, 2026-10-02)

Page order and groups (`pages`, `_render_page`):
- A page is a sheet-sized SVG (D5) keyed by `render_id(page.id)`, ordered by `(drawing_set.number, page.number)`.
- Its groups come in a fixed order: unit outlines, symbols, routes, junctions, markers, labels.
- `pages` is pure: the same model digest gives the same bytes.
- Outlines draw first, render's own call, so nothing else's stroke is ever covered by the boundary.
- A page with no outline record returns `""` for that group.
- `routes_group`: each route is one `<polyline>`, in `id` order. `.wire` gets its stroke and fill from the `<style>` block, so no element carries its own.
- Frame, grid and title block are not drawn here (D9).

Checks (`check.py`, D12):
- `UNKNOWN_SYMBOL_KEY`, `LIBRARY_VERSION_MISMATCH` and `LAYOUT_MISSING` are the three codes left here.
- A placement already reported as unknown is skipped by the version check, since a version of a symbol absent from the library means nothing.
- `LAYOUT_MISSING` is one model-wide finding with no subject, raised when `schematic_functions(model)` (model-0039) is non-empty and no `layout.page` exists.
- `PIN_MAP_INCOMPLETE` moved to `fransys_layout.stages.resolve` (layout-0041): that stage already computes the exact port binding and the model stores none of its inputs, so render does not duplicate it. `LAYOUT_MISSING` has no subject because there is no page to attach a per-function finding to.
- A board-only or cable-only model must not trip it. Layout and this check share that one predicate, since render never imports layout.

Junction dots (render-0004, D8, D15):
- A dot goes where three or more directions of one net's wire leave a point, and nowhere else.
- A net's wire segments on a page are its routes' segments and its markers' stubs. A marker stub is drawn wire.
- A segment through a point gives two directions, a segment ending there one, collinear overlaps once.
- A symbol pin is not a wire segment: two wires meeting only at a port are no junction. A wire joining another one grid out from a port gets the dot at the T.
- Segments group by `net_of` (decision 0019), because a junction only forms within one net.
- A marker's stub runs from the port along its facing. For a reference leaving its wired port sideways (I4, M7) it runs from `via` along the wire, E or W, as far as `box_x` puts the box centre.
- Coordinates are integer grid units and segments are orthogonal, so every test is an exact integer comparison.

Link markers (D8, layout-0038, model-0037, layout-0043, render-0005):
- Draw order inside a marker: stub (`<line>`, one wiring-grid step), arrow-shaped box (`<polyline>`, closed), text (`<text>`, centred).
- Box size is `marker.width`/`marker.height`, read verbatim, never measured (D7, D1). Render decides no box geometry of its own.
- Box position mirrors `fransys_layout.stages.references.marker_boxes.marker_box` (a four-way match on facing). The formula is duplicated, since render never imports layout.
- Facing is the stored `LinkMarker.facing` of an off stub. Every other marker takes it from the one port of its owning placement's oriented symbol that lands on the marker's `(x, y)`. Zero or several matches raise; there is no fallback direction. The owning placement is the one on the marker's page whose function matches the marker port's function.
- `stub_end` is the arrow's tip vertex and the box's near-edge coordinate: stub and box touch at one point. The arrow pulls the two near corners in by `MARKER_ARROW_DEPTH_G`. The far corners stay square.
- A harness line's stub (HL18, layout-0158) draws no stub. Its line runs on to the middle of the box's near edge. The box is a plain rectangle, as a shared box.
- A shared box (R6 D2, layout-0054) is a closed rectangle across the bundle row. A box beside its stub draws its lead in the same polyline, from the stub end along the near edge. A bundle's box and a packed row's have no stub. E and W markers have none either.
- Marker text uses `class="label"`, since `.marker`'s stroke-only rule would leave it invisible. It sets `text-anchor="middle"` inline, as a marker's text centres in its own box (labels do not).
- Text is centred in the box width. Its top inset is `(marker.height - profile.text_height) / 2`, read from the record and not from `marker_padding`.
- Centred in the box width means the text clears both edges once the box is `text_width + 2 * marker_padding` wide (layout-0043). `font_size_mm` is a bare number, since the viewBox makes one user unit one mm.
- A `vertical` marker (render-0005) is rotated -90 degrees about each line's anchor, lines side by side along x. A turned marker (M7) branches from `via`, E or W, to the stub under the box centre, then draws as a vertical one facing the way `via` lies from the port.
- A vertical marker's lines are centred on the record's width and on the box's length. A turned marker's text runs along the stub, and the junction dot at `via` comes from `_junctions`.

Bound leads (TL3, render-0002):
- A `Line` bound to a port draws only if that port has a route end, a link marker, or a marking label on it. An unbound line always draws.
- Route ends and markers match by exact grid position. A marking label matches by `slot`: layout writes `marking.<port name>`, and its box sits beside the port.
- Layout is unchanged by this: ports keep their positions, since `oriented_symbol` already carries `placement.orientation` into the port positions. `visible_symbol` keeps any element that has no `port` attribute, whatever its shape.
- The slot is scoped to the owning placement by the label's subject port's function, so same-named slots on two placements cannot collide.

Labels (D7, D10, C19):
- Every text is an XML-escaped `<text>` element, never a path, in the font family `Liberation Serif, Times New Roman, serif`.
- Slot texts are not drawn from the symbol.
- No font width table lives here. A label is anchored at its recorded `x`, `y`; the vertical anchor is the baseline from the font's ascent ratio.
- A label is `not-installed` only when its subject is a function or port whose item has `installed=False`. A conductor label never is.
- A coil's contact image (C19) is a header NO | NC, a thin rule, a divider between the columns, then the entries, at the label's measured box.

Unit outlines (units U1, I2a): layout writes one `layout.outline` per black box and its title as a label (slot `outline_title`). Render draws each record's rectangle, dash-dot, and measures nothing. The title reads `<unit title> rev <revision>` (U1).

Symbols (D6, D10, render-0001):
- The recipe is `LIBRARY.get`, then `repeat`, then `orient`. `GENERIC_BOX_KEY` builds `generic_box` from the placement's function's model ports, named `<function>.<port>` as layout named them, sorted as `resolve` sorts them (R7 B2, layout-0042).
- A key neither generic nor in the library gives `None`: `pages` draws an 8x8 placeholder rectangle with the key as text, and `check` reports `UNKNOWN_SYMBOL_KEY`.
- A real body is `to_fragment(oriented_symbol(...))` under `translate(x_mm,y_mm) scale(module_mm)`. The toolkit draws in raw module units, so the transform scales first and translates second. Orientation is already baked into the element coordinates.
- `to_grid` and `grid_to_mm` are small duplicates of facts private to other packages. They are not algorithms.
- `to_grid` multiplies by 8, exact for a multiple of 0.125. `grid_to_mm` divides `module_mm` by 8, a power of two, so the `Decimal` is exact (0.3125 mm for `module_mm=2.5`).
- A `not-installed` placement's `<g>` carries `class="symbol not-installed"` (D10). `_leads.visible_symbol` drops unwired bound leads before the fragment is built. A fan-out leg ending on a port wires it, as a route end does (layout-0158).
- A placement is `not-installed` when `functions(model)[placement.function].item` has `installed=False`.

Numbers (`format_decimal`): `normalize()` drops trailing zeros but can leave `1E+1`, so that case is re-quantized to an integer and written with `:f`, which never emits an exponent. Every zero shape becomes `0`: `normalized == 0` catches them all, since `Decimal` equality ignores the sign of zero.

Style block (D11, D10, U1):
- Seven classes: `symbol`, `wire`, `junction`, `marker`, `label`, `not-installed`, `unit-boundary`. Black on white, no wire colours, `label` sets D7's font family.
- `unit-boundary` is IEC 60617's dash-dot line: long dash, gap, dot, gap, the dot one `STROKE_WIDTH_MM` long. The patterns are render's own choice.
- Stroke widths and dash arrays are bare numbers, not `mm` lengths. `0.25mm` compiled to about 0.93 mm on Typst/resvg. A bare `0.25` is 0.25 user units, since the viewBox makes one unit one mm (D5). `tests/test_stroke_width_compiles_correctly.py` proves it on pixels.
- `not-installed` is written for a stroke-only shape: dashed grey outline, no fill (D10). `text.not-installed` is solid grey fill, no stroke, no dash. It is more specific than `.not-installed`, whose `fill: none` would leave a label as a thin dashed outline.
- A real symbol's line weight is the toolkit's own `0.1` module units, scaled to mm by the ancestor transform. `.symbol`'s rule never reaches those descendants.
- `.not-installed *` (stroke) and `.not-installed [fill]` (fill, only a filled shape) override the toolkit's inline attributes on Typst's SVG output. `tests/test_symbol_not_installed_compiles_grey.py` proves it.
- The `.not-installed *` stroke width alone divides by `module_mm`: it is read inside the `scale(module_mm)` transform, and a bare `0.25` there rendered 0.625 mm on the house sheet.
- Render count test (render-0006, floor 100): `tests/test_render_scale_counts.py` fails when any render code object's calls, resumes or loop turns grow over 2.5x per doubling of build_scale; it shares `tests/scale_counter.py` with layout's.
