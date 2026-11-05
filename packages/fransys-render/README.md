# fransys-render

Fransys output: a core `Drawing` to SVG, plus cable blocks, block-diagram sheets, bridge pieces and page backgrounds.

Output contract: pure function of its input returning str or a mapping of str. No file I/O, no clock, no randomness. Same input, same bytes.

- `svg(drawing, library, style, *, sheet_mm=None)` draws one core `Drawing` (render-0022); with `sheet_mm` it writes a sheet-sized SVG with the drawing at the content box (render-0027). It imports no model.
- `sheets(document_sheets)` draws each page background: frame, reference grid and title block, from symdef data (render-0019). `sheet_check` reports the title-block findings of those sheets.
- `check(model)` reports `REFERENCE_OFF_DOCUMENT` (model-0258). It is rebuilt from pages and membership in the reader half of DEL-4.
- `cable_blocks(model, cables, library)` draws the `CableLayout` blocks (render-0007, layout-0408). `diagram_sheets(model)` draws the block-diagram sheets (render-0009) from their records. They stay, with the shared chain `_symbols`, `_symbol_geometry`, `_cable_*` and `_diagram_*`, until P7.8 and P7.9 delete their engines.
- `bridge_pieces()` draws the two bridge mark drawings for pdf.
- `FINDING_CODES` lists the codes this package emits.

Deleted by DEL-4 (render-0028): the old page drawer `pages` and the modules only it reached. Those modules are outlines, symbols group, routes, junctions, labels, markers, fan-outs, harness boxes, leads, tints and drawn shorts. The `DRAWING_SHORTS_NETS`, `UNKNOWN_SYMBOL_KEY` and `LIBRARY_VERSION_MISMATCH` checks go with them. Their history is in decisions render-0001 to render-0026.
