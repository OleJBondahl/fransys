# Layout numbers

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page lists every keyword of `d.layout.profile`: what it does, its house value, its effect on the drawing, and when to change it.
A gap is in grid units `G`; eight `G` make one symbol module.

## Sheet

A document's sheet is set for the whole build with `fr.settings(paper=...)` and `paper_by_kind` (see settings.md): A3 or A2, landscape. No call of a design or a unit sets or changes a sheet.

## Profile keywords

`d.layout.profile(...)` sets the layout numbers of the design, or of the unit whose body calls it. At most one per unit. A keyword left out keeps its house value. A value given replaces it whole. A unit with no profile uses the house values, never its parent's. `d.layout.profile` does not draw anything: it advises the layout engine.

| keyword | house value | what it does | effect on the drawing | when to change it |
|---|---|---|---|---|
| `hide_unused_pins` | `False` | Hide a box-drawn pin with no conductor, and a function with none, on drawings only. | Drawings are shorter; every list still shows every pin. A box in a chain draws only its wired pins (LONG-CHAIN D2). | An interface with many unused pins. |

## Grid pitch and printed sizes

`module_mm` sets the grid pitch and must equal the library's 2.5: symbols never scale. A crowded page is never fixed by size. Split the content into function blocks (`drawing.md`). A well-formed design that still overflows is a Fransys defect: send the smallest model.
The text sizes are the library's fixed heights, not a profile keyword and not a setting. Never use the text size to make a page fit: a page that is too full needs less on the page, split into function blocks.
