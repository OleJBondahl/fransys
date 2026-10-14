# Layout numbers

This page lists every keyword of `d.layout.profile` and every number of `d.layout.sheet`: what it does, its house value, its effect on the drawing, and when to change it.
A gap is in grid units `G`; eight `G` make one symbol module. A sheet number is in millimetres, except `module_mm`.

## Sheet numbers

`d.layout.sheet(name, **numbers)` records a sheet format and returns its handle. Pass the handle to `d.layout.profile(sheet=handle)`. A profile with no `sheet` uses the house sheet: A3 landscape, 420 by 297 mm, content box 410 by 267 mm at (5, 5), an 8 by 6 frame, `module_mm` 2.5. A sheet takes all nine numbers and has no defaults. A missing number or an unknown one raises `AuthorError`.

| number | what it is | effect on the drawing | when to change it |
|---|---|---|---|
| `width_mm` | Sheet width. | The size of the printed page. | A different paper size. |
| `height_mm` | Sheet height. | The size of the printed page. | A different paper size. |
| `content_x_mm` | Left edge of the content box, from the sheet's left edge. | Where drawings start; the margin on the left. | A different margin. |
| `content_y_mm` | Top edge of the content box, from the sheet's top edge. | Where drawings start; the margin on top. | A different margin or title block. |
| `content_width_mm` | Width of the content box. | Page capacity: a page holds `content_width_mm * 8 / module_mm` `G` across, rounded down. A wider box fits more columns before a block is split. | A different paper size. |
| `content_height_mm` | Height of the content box. | Page capacity down the page, by the same rule. A taller box fits more rows. | A different paper size. |
| `frame_columns` | Columns of the reference grid printed on the frame. | The content box is divided evenly. Cross references and findings name a position as a column and a row. | Rarely; more columns on a wide sheet. |
| `frame_rows` | Rows of the reference grid. | The same, for rows. | Rarely. |
| `module_mm` | Millimetres of one symbol module. Number or `Decimal`. | The grid pitch. Symbol bodies and gaps scale with it; text sizes and line widths do not, they are fixed in mm. A smaller module fits more on a page; a larger one splits sooner. | The first thing to change when a page is too crowded. |

```python
from decimal import Decimal

import fransys as fr

d = fr.design("demo_parts")
a4 = d.layout.sheet(
    "A4 landscape",
    width_mm=297,
    height_mm=210,
    content_x_mm=5,
    content_y_mm=5,
    content_width_mm=287,
    content_height_mm=170,
    frame_columns=6,
    frame_rows=4,
    module_mm=Decimal("2.0"),
)
d.layout.profile(sheet=a4)
```

## Profile keywords

`d.layout.profile(...)` sets the layout numbers of the design, or of the unit whose body calls it. At most one per unit. A keyword left out keeps its house value. A value given replaces it whole. A unit with no profile uses the house values, never its parent's. `d.layout.profile` does not draw anything: it advises the layout engine.

| keyword | house value | what it does | effect on the drawing | when to change it |
|---|---|---|---|---|
| `sheet` | the house sheet | The sheet format the pages use, a handle from `d.layout.sheet`. | Paper size, margins and `module_mm`. | A paper size other than A3. |
| `column_gap` | 48 | Clear width between two adjacent columns of blocks. | Wider gaps spread columns and leave room for wires between them. | Wires cramp between columns, or columns waste width. |
| `row_gap` | 32 | The smallest clear height between two blocks stacked in a column. | A column too tall for its page closes its spacing down to this value and no further. | Rarely; lower it to fit a tall column. |
| `row_spacing` | 88 | The clear height a block keeps below the one above it, when the page has room. | Looser spacing reads easier; it falls back toward `row_gap` on a full page. | A sparse page that wastes height, or a crowded one. |
| `route_margin` | 64 | How far outside the box spanned by a wire's two ends the router may look first. | A larger margin finds a detour round a block; a smaller one keeps wires short. | A wire takes a long way round, or cannot find a way. |
| `text_height_mm` | 1.8 | The smallest text on every page kind, a capital height in mm (ISO 3098); a larger role keeps its own size or this one, whichever is larger. | Sets text size, and with it the room texts take: font size over one `G`, rounded up. | A style choice only. See below. |
| `min_text_height_mm` | 1.8 | The smallest capital height in mm the text may print at. | Changes no drawing. A profile printing under the floor gets one `TEXT_TOO_SMALL` warning, and nothing is shrunk or grown. | The recommended floor is the house 1.8. Lower it only when the small text is intended. Otherwise raise `text_height_mm`. |
| `marker_padding` | 2 | Clear space between a link marker's text and its outline, on every edge. | Larger padding makes markers and their boxes bigger. | Markers look cramped. |
| `route_turn_penalty` | 4 | The cost of one bend in a wire. | A higher cost makes wires straighter and longer. | Wires zigzag. |
| `route_crossing_penalty` | 16 | The cost of one wire crossing another. | A higher cost avoids crossings at the price of longer wires. | Too many crossings. |
| `hide_unused_pins` | `False` | Hide a box-drawn pin with no conductor, and a function with none, on drawings only. | Drawings are shorter; every list still shows every pin. A box in a chain draws only its wired pins (LONG-CHAIN D2). | An interface with many unused pins. |
| `actuator_each_contact` | `True` | Draw the operated symbol on every contact of a manually operated device, with no reference and no contact list. | `False` draws the actuator once at the lead contact, with the contact list under it. | A design that wants one push button per device. The choice is per unit: set it in each unit's profile, or in a shared helper every unit calls, to set it once. |
| `band_ranks` | supply 0, `terminal.first` 0, protection 1, switch and contacts 2, sensor 3, coil, load, actuator and `terminal` 4, `terminal.last` 5 | A map of function kind to the horizontal band it sits in, top first. `terminal.first` and `terminal.last` sit beside `terminal`. | Moves kinds up or down the column. The map replaces the house map whole: restate every kind you want ranked. | A circuit reads better with another top-to-bottom order. |
| `group_ranks` | empty | A map of an aspect group's label to its page rank. | Orders the groups of pages. A group with no rank sorts last. | You want the pages in your own order. |

## Grid pitch and printed sizes

`module_mm` sets the grid pitch, not the printed size of text or lines, which are fixed in mm. To make a crowded page fit, make `module_mm` smaller; the page then holds more `G`. A larger one gives more pages.
`text_height_mm` sets the smallest text on every page, as a capital height in mm. Never use it to make a page fit: a page that is too full needs a smaller `module_mm` or less on the page.
