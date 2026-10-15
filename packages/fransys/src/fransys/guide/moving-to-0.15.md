# Moving to 0.15

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page lists each call, name and finding that 0.15 changes, with the old spelling and the new one.
A consumer script that used an old spelling changes as below. The version is read with `importlib.metadata.version("fransys")`; there is no `fr.__version__`.

## Renamed and changed names

| old | new | why |
|---|---|---|
| `text_height` in `layout.profile(...)`, an int in `G`, default 8 | `text_height_mm`, a Decimal in mm, default 1.8 | The text size is a capital height in mm (ISO 3098), not a count of grid units. |
| `min_text_mm` in `layout.profile(...)` | `min_text_height_mm`, default 1.8 | It is the floor for `text_height_mm`, in the same unit. |
| `text_mm` and `min_text_mm` on a readability page row | `text_height_mm` and `min_text_height_mm` | The same two quantities under the new names. A unit row takes the smallest `text_height_mm`. |
| `module_mm` scales symbols, gaps and text | `module_mm` sets the grid pitch only | Text and line widths are fixed in mm. Set the text size with `text_height_mm`. |
| `TEXT_TOO_SMALL` reads `text_height` and `min_text_mm` | reads `text_height_mm` and `min_text_height_mm` | The finding compares the same two values under the new names. |

## New keyword

| old | new | why |
|---|---|---|
| `fr.write(result, out_dir)` | `fr.write(result, out_dir, releases=into)` | `releases` is the folder you pass to `fr.release`. It defaults to `None`, which marks nothing. |

## The system overview

`fr.write` writes `overview.html` beside the PDFs. The page is one file and needs no network. Its switches are Colour by, Find, Parts, Select and Theme, and View inside a unit.

- **Changes** is new. It appears only when `releases` holds a release of the system, the one at the model's revision or else the previous one.
- Without `releases`, or with no release there, the page has no Changes switch.
- The Changes switch applies only to a whole-system write; a unit write gets no Changes page.

## Drawing and readability

- `d.ac_supply` no longer draws power symbols at its pins; it keeps AC rails as terminals and references.
- The readability rows have a new column, `single_contact_images_other_page`, counting the single-contact images whose one contact is on another page.

## Checks and findings

- `check` now places `overview.html` and returns its findings, so a whole-system or unit `write` meets them at the same gate. `build` does not.
- `OVERVIEW_UNPLACED` is new. It is an `ERROR`, raised when the overview placer finds no room for a view.
- The `DIAGRAM_BOX_OVERLAP`, `DIAGRAM_LINE_OFF_BOX`, `DIAGRAM_LINE_THROUGH_BOX` and `DIAGRAM_TEXT_OVERLAP` findings also check the views of the overview.
