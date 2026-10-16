# The system overview

`overview.html` is one file that `fr.write(result, out_dir)` puts beside the PDFs. It needs no network and no server: open it in a browser. This page says how to read it.

The page starts at the system: each cabinet unit is a box, each cable a line. Double-click a unit, or select it and press Enter, to open it; the crumbs above the drawing and "Up one level" go back. A unit opens as its function groups, as all devices with strips drawn through, as lanes when it has them, or as plain boxes: pick one under "View". A stub opens its far side in place.

- **Colour by** a unit, a function group, an item kind or a location. The legend counts the boxes of the level shown; click a class to hide it, and a chip above the drawing brings it back.
- **Find** an item by designation in the search box; Enter opens its level and selects it.
- **Parts** on the left lists every item as a tree; the boxes hide an item and what it holds.
- **Select** a box or line to dim the rest and list its facts and the signals through it on the right. An item drawn on a PDF page lists its pages, each a link to that page. Keep the HTML and the PDFs together in the folder `write` made.
- **Theme** is light, dark or your system's. The address holds the whole view, so Back, Forward and a copied link return to it.

With no document in the build there is no PDF, so the page has no links. The page holds no internal id, so a rename that changes no printed text changes no byte of it.
