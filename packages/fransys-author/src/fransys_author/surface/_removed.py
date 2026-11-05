"""The removed attributes of `fr`, Design, Detail, Layout, Fn and Terminal, each with its new spelling."""

from typing import NamedTuple, NoReturn

from fransys_author.errors import AuthorAttributeError


class Removed(NamedTuple):
    """One removed attribute: its owner, name, one-line text and guide anchor."""

    owner: str
    name: str
    text: str
    anchor: str


def _rows(owner: str, names: str, anchor: str, text: str) -> tuple[Removed, ...]:
    return tuple(Removed(owner, name.strip(), text, anchor) for name in names.split(","))


REMOVED: tuple[Removed, ...] = (
    *_rows("fr", "ABOVE, BELOW", "removed-side", "removed on purpose: the side hint was inert (R1486)"),
    *_rows("fr", "IT, EARTHED", "removed-earthing", "removed on purpose: supplies are the earthed default only (R1494)"),
    *_rows("fr", "BuildErrors", "removed-build-errors", "use fr.BuildFailedError"),
    *_rows("fr", "MergeConflict", "removed-merge-conflict", "use fr.MergeConflictError"),
    *_rows("Design", "busbar", "removed-busbar", "use d.detail.busbar(a, b)"),
    *_rows(
        "Design",
        "rating, operating",
        "removed-rating-operating",
        "removed on purpose: unit-boundary facts (R1490); read part data through the part's elecdef Rating",
    ),
    *_rows("Detail", "wire", "removed-detail-wire", "use d.series(a, b, wire=w); label= and n= have no replacement"),
    *_rows("Detail", "star", "removed-detail-star", "use one d.series(src, t, wire=w) per target"),
    *_rows("Detail", "net", "removed-detail-net", "removed on purpose: declared nets; connect with d.series"),
    *_rows(
        "Detail",
        "rail_bond",
        "removed-rail-bond",
        "declare the rail with rail=True; bond PE with d.series(incoming_pe, pe, wire=(GNYE, 1.5))",
    ),
    *_rows("Layout", "chain", "removed-layout-chain", "removed on purpose: d.series names the path and layout reads it (R1490)"),
    *_rows("Layout", "page_title", "removed-page-title", "removed on purpose: the default page title stays (R1490)"),
    *_rows("Layout", "symbol", "removed-layout-symbol", 'set `symbol = "..."` on the part file\'s [[function]] entry'),
    *_rows(
        "Layout",
        "break_before",
        "removed-break-before",
        "removed on purpose: Fransys paginates; order with d.layout.order(*groups) (R1490)",
    ),
    *_rows("Layout", "keep_together", "removed-keep-together", "removed on purpose (R1490)"),
    *_rows("Layout", "draw_in", "removed-draw-in", "removed; d.series and group= place it"),
    *_rows("Layout", "pins_below", "removed-pins-below", "removed on purpose: the engine draws the box; hide_unused_pins stays"),
    *_rows("Layout", "side", "removed-side", "removed on purpose: the side hint was inert (R1486)"),
    *_rows("Fn", "limits", "removed-fn-limits", "removed on purpose: unit-boundary facts (R1490)"),
    *_rows("Terminal", "limits", "removed-fn-limits", "removed on purpose: unit-boundary facts (R1490)"),
    *_rows("Layout", "sheet", "removed-profile-numbers", "removed on purpose; A3 or A2 landscape via fr.settings(paper=...)"),
)

_BY_KEY = {(row.owner, row.name): row for row in REMOVED}


def refuse(owner: str, name: str) -> NoReturn:
    """Raise the error for a missing attribute `name` of `owner`: the table text if it was removed.

    Private names (`_x`) are never in the table, so copy and pickle probes see an AttributeError.
    Does not return: it always raises. The table is deleted at the 0.23 tag.
    """
    row = _BY_KEY.get((owner, name))
    if row is None:
        msg = f"{owner!r} has no attribute {name!r}"
        raise AuthorAttributeError(msg)
    msg = f"{owner}.{name} is removed in 0.22: {row.text}; see moving-to-0.22#{row.anchor}"
    raise AuthorAttributeError(msg)
