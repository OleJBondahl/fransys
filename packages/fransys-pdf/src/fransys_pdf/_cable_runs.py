"""Cable drawing pages grouped by part (pdf-0020): one run per part number, blocks inside it.

A run is one Typst `#page` whose header carries the part line (pdf-0021), so a run that flows onto
further pages repeats it there, with " (cont.)" after it. Its cable blocks fill a column
from the top, then the next column to the right, then a new page; a block always stays whole.
A block taller than the page body never reaches the flow: `check` stops it first (pdf-0022).
"""

from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from ._frame import text_margin
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.layout import SheetFormat

NO_PART = "No part number"
_PADDING_MM = 5  # `_frame`'s R4 padding on each side of the content box
_HEADER_MM = 11  # extra top margin: the part line and a 4 mm gap below it (pdf-0021)


class Block(NamedTuple):
    """One cable block of a run: its `svgs` key, its run's part number and that run's part line."""

    key: str
    mpn: str
    line: str


def body_size_mm(sheet: SheetFormat) -> tuple[int, int]:
    """The width and height in mm that a run's blocks may fill on `sheet`'s page body."""
    return (
        sheet.content_width_mm - 2 * _PADDING_MM,
        sheet.content_height_mm - 2 * _PADDING_MM - _HEADER_MM,
    )


def part_groups(blocks: Iterable[Block]) -> list[tuple[str, list[Block]]]:
    """`blocks` grouped by part number, parts sorted by it, blocks in their given order.

    Blocks with no part number form the last group, headed `NO_PART`.
    """
    groups: defaultdict[str, list[Block]] = defaultdict(list)
    for block in blocks:
        groups[block.mpn].append(block)
    ordered = [*sorted(key for key in groups if key), *([""] if "" in groups else [])]
    return [(key or NO_PART, groups[key]) for key in ordered]


_FLOW = """
#context {
  let (W, H, gap, vgap) = (%(w)s, %(h)s, %(gap)s, 4mm)
  let items = (%(items)s)
  let out = ()
  let pages = ()
  let cols = ()
  let used = 0pt
  let col = (w: 0pt, h: 0pt, items: ())
  for c in items {
    let w = calc.min(measure(c).width, W)
    let h = measure(block(width: w, c)).height
    if col.items.len() > 0 and (col.h + vgap + h > H or used + calc.max(col.w, w) > W) {
      cols.push(col)
      used += col.w + gap
      col = (w: 0pt, h: 0pt, items: ())
      if used + w > W { pages.push(cols); cols = (); used = 0pt }
    }
    col.h = if col.items.len() > 0 { col.h + vgap + h } else { h }
    col.w = calc.max(col.w, w)
    col.items.push(c)
  }
  if col.items.len() > 0 { cols.push(col) }
  if cols.len() > 0 { pages.push(cols) }
  for (n, p) in pages.enumerate() {
    if n > 0 { pagebreak() }
    stack(dir: ltr, spacing: gap, ..p.map(k => block(width: k.w, stack(dir: ttb, spacing: vgap,
      ..k.items.map(c => block(breakable: false, c))))))
  }
}
"""


def _flow(bodies: list[str], width_mm: float, height_mm: float) -> str:
    """The run's cable blocks laid in columns: down a column, then right, then a new page.

    A column is as wide as its widest block. A block never splits across pages.
    """
    items = "".join(f"[{body}], " for body in bodies)
    return _FLOW % {
        "w": f"{width_mm:g}mm",
        "h": f"{height_mm:g}mm",
        "gap": f"{_PADDING_MM}mm",
        "items": items,
    }


def _header(heading: str, label: str) -> str:
    """The page header: the part number, plus " (cont.)" on every page after the run's first."""
    return (
        f"context {{ let first = query(label({literal(label)})).first().location().page(); "
        f'strong(text({literal(heading)} + if here().page() > first {{ " (cont.)" }})) }}'
    )


def run_page(
    sheet: SheetFormat, index: int, heading: str, background_source: str, bodies: list[str]
) -> str:
    """One part's run: a `#page` with the part heading as header, each cable block in turn."""
    label = f"run-{index}"
    width, height = body_size_mm(sheet)
    margin = f"{{ let m = {text_margin(sheet)}; (..m, top: m.top + {_HEADER_MM}mm) }}"
    blocks = _flow(bodies, width, height)
    return (
        f"#page(margin: {margin}, header-ascent: 4mm, header: {{ {_header(heading, label)} }}, "
        f"background: {background_source})[#metadata(none) <{label}>\n{blocks}]"
    )
