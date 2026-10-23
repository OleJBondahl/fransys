Fransys output: a core `Drawing` to SVG, plus cable blocks, block-diagram sheets, bridge pieces and page backgrounds.

Output contract: pure function of its input returning str or a mapping of str. No file I/O, no clock, no randomness. Same input, same bytes.

- `svg(drawing, library, style, *, sheet_mm=None)` draws one core `Drawing` (render-0022); with `sheet_mm` it writes a sheet-sized SVG with the drawing at the content box (render-0027). It imports no model.
- `sheets(document_sheets)` draws each page background: frame, reference grid and title block, from symdef data (render-0019). `sheet_check` reports the title-block findings of those sheets.
- `check(model, built)` reports `LAYOUT_MISSING` and `REFERENCE_OFF_DOCUMENT` (model-0258). `LAYOUT_MISSING` is the guard when the core makes no page for connected functions; `REFERENCE_OFF_DOCUMENT` is rebuilt from pages and membership in the reader half of DEL-4.
- `cable_blocks(model)` and `diagram_sheets(model)` draw the cable blocks (render-0007) and block-diagram sheets (render-0009) from their records. They stay, with the shared chain `_symbols`, `_symbol_geometry`, `_style`, `_cable_*` and `_diagram_*`, until P7.8 and P7.9 delete their engines.
- `bridge_pieces()` draws the two bridge mark drawings for pdf.
- `FINDING_CODES` lists the codes this package emits.

Deleted by DEL-4 (render-0028): the old page drawer `pages` and the modules only it reached (outlines, symbols group, routes, junctions, labels, markers, fan-outs, harness boxes, leads, tints, drawn shorts), with the `DRAWING_SHORTS_NETS`, `UNKNOWN_SYMBOL_KEY` and `LIBRARY_VERSION_MISMATCH` checks. Their history is in decisions render-0001 to render-0026.
