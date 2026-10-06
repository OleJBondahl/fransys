"""T6: which end of a signal a reference text stands at and where it leaves, by `MARKER_ENDS`."""

from functools import cache
from typing import NamedTuple, cast

from fransys_layout.conventions import FACTS, fact, first_match, validate
from fransys_layout.conventions.references import MARKER_ENDS
from fransys_layout.stages.types import MarkerSide

from .types import Leave

SITES = ("star_ref", "star_branch", "split", "cut", "off_stub", "rail_branch")


class EndRead(NamedTuple):
    """One text's decision site and the three things its end is read from."""

    site: str
    by_designation: bool = False
    earlier: bool = False
    at_home: bool = False
    terminal: bool = False


@fact("marker_site", kind="drawing", values=SITES)
def _marker_site(end: EndRead) -> str:
    """Which decision builds this text."""
    return end.site


@fact("by_designation", kind="drawing")
def _by_designation(end: EndRead) -> bool:
    """The star's reference is named by designation: it has more or fewer than one point."""
    return end.by_designation


@fact("earlier_page", kind="drawing")
def _earlier_page(end: EndRead) -> bool:
    """This end of a cut stands on the earlier page."""
    return end.earlier


@fact("at_home_page", kind="drawing")
def _at_home_page(end: EndRead) -> bool:
    """This end of a split stands on the page of the terminal's own column."""
    return end.at_home


@fact("terminal_function", kind="physical", source="terminal strip (IEC 60947-7)")
def _terminal_function(end: EndRead) -> bool:
    """The end's function is a terminal."""
    return end.terminal


validate(MARKER_ENDS, FACTS)


@cache
def marker_end(read: EndRead) -> tuple[MarkerSide, Leave]:
    """The side and the leaving of a text: the first row of `MARKER_ENDS` that holds."""
    row = first_match(MARKER_ENDS, read, FACTS)
    if row is None:
        msg = f"no marker end for {read}"
        raise ValueError(msg)
    side, leave = cast("tuple[str, str]", row.then)
    return MarkerSide(side), Leave(leave)
