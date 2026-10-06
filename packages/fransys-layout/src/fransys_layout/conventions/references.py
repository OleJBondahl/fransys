"""The tables of the reference markers: the link case (T7) and the marker ends (T6).

Both are first-match tables. `LINK_CASE` names the case of a cut; its last row always holds, so a
cut that no earlier row takes is severed. `MARKER_ENDS` gives, per decision site, which end of a
signal the text stands at and which of its function's ports it leaves by, as the `.value` strings
of `MarkerSide` and `Leave`; the stages map them back. A cut or off-stub text leaves by `port`,
the default of its decision.
"""

from .rows import Row, Table, all_, any_, not_

LINK_CASE = Table(
    "link case",
    "first match",
    (
        Row("T7.1", "crosses_unit", "cross_unit"),
        Row("T7.2", "terminal_on_both_pages", "terminal_echo"),
        Row("T7.3", "same_item", "tag_echo"),
        Row("T7.4", any_("crosses_unit", not_("crosses_unit")), "severed"),
    ),
)

_STAR = ("marker_site", "star_ref")
_SPLIT = all_(("marker_site", "split"), "terminal_function")
_CUT = ("marker_site", "cut")

MARKER_ENDS = Table(
    "marker ends",
    "first match",
    (
        Row("T6.1", all_(_STAR, "by_designation"), ("owner", "port")),
        Row("T6.2", _STAR, ("owner", "free")),
        Row("T6.3", ("marker_site", "star_branch"), ("user", "free_or_port")),
        Row("T6.4", all_(_SPLIT, "at_home_page"), ("owner", "south")),
        Row("T6.5", _SPLIT, ("user", "north")),
        Row("T6.6", all_(_CUT, "earlier_page"), ("owner", "port")),
        Row("T6.7", _CUT, ("user", "port")),
        Row("T6.8", ("marker_site", "off_stub"), ("owner", "port")),
        Row("T6.9", ("marker_site", "rail_branch"), ("user", "free_or_port")),
    ),
)
