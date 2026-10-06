Fransys output: interactive system overview HTML.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

- `html(model) -> str`: one self-contained page over `overview_graph`: every item a box (nested by parent), every connection a line, click an item or a link to trace its signals. No network: the graph library, the data and the page script are inline. The decision: `docs/decisions/overview-0001-overview-page.md`.
- Cytoscape.js 3.34.3 is vendored as the generated module `_vendor_cytoscape.py` (MIT licence: `LICENSE-cytoscape.txt`). To change it, download the release file from the npm package and run `uv run python packages/fransys-overview/scripts/vendor_cytoscape.py <cytoscape.min.js> <version>`; the script does no network access.
  - An output reads no file, so the library is a generated module holding the source as one string constant, not a data file read at run time. Record the download's origin and sha256 in `docs/decisions/overview-0001-*.md`. The script writes only `src/fransys_overview/_vendor_cytoscape.py`. The source is ASCII in chunks under 100 columns, so line-ending or encoding conversion leaves it unchanged, it needs no lint exclusion and it stays greppable. The script joins the chunks back and compares them with the bytes read before it reports success.
- The page script `_app.py` is hand-written ES2020: no framework, no build step, nothing random, no clock, no network. It reads the embedded data block and draws it with the vendored library. Text from the data goes on the page as `textContent` only, never as markup. A click on the background does nothing, so a misclick cannot clear a trace; Escape and the Reset button do.
- The page lays itself out in the browser, and the page bytes do not depend on that layout.
- `_template.fill` replaces each `@@NAME@@` token in one pass, so a value that contains token text is never rescanned; the template's tokens and the value names are the same set, else `ValueError`.

Status: `html` implemented. The page script is checked as text in the tests (there is no browser in CI) and was checked by hand in Chrome.
