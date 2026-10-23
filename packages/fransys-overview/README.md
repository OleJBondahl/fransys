Fransys output: interactive system overview HTML.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

- `html(model) -> str`: one self-contained page. It draws the views `derive.overview_view_rows` gives at the positions of the `layout.overview_*` records, so `model` is the one `lay_out_overview` returns. Drill from the system to a unit, a function group or a strip. Colour by unit, group, kind or location, and filter by legend. Search, trace a box or line, and follow a link to a drawing page of the PDF. The decisions: `docs/decisions/overview-0001-overview-page.md` and `overview-0002-the-page-draws-the-records.md`.
- No Id reaches the page: things are named by table index in printed order, so a rename changes no byte. No layout runs in the page. It reads `derive` rows only (the placed rows of `derive.overview_placed_views`), never a `layout` or `vocab` record.
- Cytoscape.js 3.34.3 is vendored as the generated module `_vendor_cytoscape.py` (MIT licence: `LICENSE-cytoscape.txt`). To change it, download the release file from the npm package and run `uv run python packages/fransys-overview/scripts/vendor_cytoscape.py <cytoscape.min.js> <version>`; the script does no network access.
  - An output reads no file, so the library is a generated module holding the source as one string constant, not a data file read at run time. Record the download's origin and sha256 in `docs/decisions/overview-0001-*.md`. The script writes only `src/fransys_overview/_vendor_cytoscape.py`.
- The page script is the `_js_*` modules joined by `_app.py`: hand-written ES2020, no framework, no build step, nothing random, no clock, no network. Text from the data goes on the page as `textContent` only. The data is built by `_data.py`; the colours are `_palette.py`.
- `_template.fill` replaces each `@@NAME@@` token in one pass, so a value that contains token text is never rescanned; the template's tokens and the value names are the same set, else `ValueError`.

## Derive rows (moved from docs/DESIGN.md section 6)

The overview draws `derive`'s rows at `layout.overview_*`; boxes open as GROUP or STRIPS; parts tree `derive.overview_tree` (overview-0002). `check` runs that engine; schematic PDF pages are link targets (0186).

Status: `html` implemented. Tests read the page as text and data. `internal/scripts/overview_smoke.py` drives it in a headless Chromium (outside the gate).
