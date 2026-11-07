"""Cable drawing pages grouped by part (pdf-0020): one run per part number, blocks inside it.

A run is one Typst `#page` whose header carries the part line (pdf-0021), so a run that flows onto
further pages repeats it there as a continued heading. Its cable blocks fill a column
from the top, then the next column to the right, then a new page; a block always stays whole.
A block taller than the page body never reaches the flow: `check` stops it first (pdf-0022).
"""

from typing import TYPE_CHECKING

from ._geometry import text_margin
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import SheetRow

    from ._doc import Doc


def body_size_mm(sheet: SheetRow, pdf: Mapping[str, float]) -> tuple[float, float]:
    """The width and height in mm that a run's blocks may fill on `sheet`'s page body, by the `[pdf]` margin and header."""
    return (
        sheet.content_width_mm - 2 * pdf["page_margin_mm"],
        sheet.content_height_mm - 2 * pdf["page_margin_mm"] - pdf["cable_run_header_mm"],
    )


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


def _flow(bodies: list[str], width_mm: float, height_mm: float, gap_mm: float) -> str:
    """The run's cable blocks laid in columns: down a column, then right, then a new page.

    A column is as wide as its widest block. A block never splits across pages.
    """
    items = "".join(f"[{body}], " for body in bodies)
    return _FLOW % {
        "w": f"{width_mm:g}mm",
        "h": f"{height_mm:g}mm",
        "gap": f"{gap_mm:g}mm",
        "items": items,
    }


def _header(headings: tuple[str, str], label: str) -> str:
    """The page header: the part number, continued on every page after the run's first.

    `headings` is the part line and the same line carrying the continued word.
    """
    heading, continued = headings
    return (
        f"context {{ let first = query(label({literal(label)})).first().location().page(); "
        f"strong(text(if here().page() > first {{ {literal(continued)} }} "
        f"else {{ {literal(heading)} }})) }}"
    )


def run_page(doc: Doc, index: int, headings: tuple[str, str], background_source: str, bodies: list[str]) -> str:
    """One part's run: a `#page` with the part heading as header, each cable block in turn."""
    sheet, pdf = doc[3], doc[6]
    label = f"run-{index}"
    width, height = body_size_mm(sheet, pdf)
    margin = f"{{ let m = {text_margin(sheet, pdf['page_margin_mm'])}; (..m, top: m.top + {pdf['cable_run_header_mm']}mm) }}"
    blocks = _flow(bodies, width, height, pdf["page_margin_mm"])
    return (
        f"#page(margin: {margin}, header-ascent: 4mm, header: {{ {_header(headings, label)} }}, "
        f"background: {background_source})[#metadata(none) <{label}>\n{blocks}]"
    )
