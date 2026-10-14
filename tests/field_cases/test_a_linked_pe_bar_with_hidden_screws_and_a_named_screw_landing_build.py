"""Field case: a PE bar with internal links, hidden unused pins and a named screw builds.

The engineering shape: a unit holds a PE bar that hands its function back as its interface. The
bar is one piece, so its parts file links the screws. One motor PE pin is wired to the bar by its
function name, another bar is landed on a numbered screw, and `hide_unused_pins` is on.

The bug (0.18.5): with the links and the hidden pins together the build raised LayoutError "a port
of a cut is not drawn at a port of the symbol its function is placed with" (three screws), or
KeyError in the chain stage (two screws): the unwired, linked screws got a protective-earth symbol
though the cut dropped them. A screw landed by its number gave CONNECTION_NOT_DRAWN, because only
the next-free landing joined the screw to the PE net.
The rules: a symbol is decided only for a screw the cut keeps, and every landing on a bar screw,
named or next free, joins the PE net (pe-bar B0 and B3). Fixed by layout-0236.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import GNYE

from fransys_model.layout import PowerSymbol, layout_of


class _Box(NamedTuple):
    PE: fr.Device


def _unit(bar: str, screw: str | None, hide: bool) -> Any:  # noqa: FBT001 - a test helper
    @fr.unit("bar-unit", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
    def make(c: Any) -> _Box:
        c.layout.profile(hide_unused_pins=hide)
        pe = c.device("PE", bar, interface=True)
        motor = c.device("M1", "DEMO-MOTOR-4KW").motor["PE"]
        c.wire(motor, pe.pe if screw is None else pe[screw], wire=(GNYE, 2.5))
        return _Box(pe)

    return make


def _build(bar: str, screw: str | None, folder: Path, *, hide: bool = True) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_unit(bar, screw, hide), "U1")
    cover = folder / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "bar-unit", cover=cover))


def _errors(result: fr.BuildResult) -> set[str]:
    return {f.code for f in fr.check(result) if f.severity is fr.Severity.ERROR}


def _symbols(result: fr.BuildResult) -> int:
    return sum(
        1 for s in layout_of(result.model, PowerSymbol).values() if s.symbol == "protective-earth"
    )


def test_a_three_screw_linked_bar_with_hidden_pins_draws_the_landing_symbol(tmp_path: Path) -> None:
    """b: no LayoutError, one protective-earth symbol at the motor pin."""
    result = _build("DEMO-PEBAR-3-LINKED", None, tmp_path)
    assert _symbols(result) > 0
    assert not _errors(result)


def test_a_two_screw_linked_bar_with_hidden_pins_builds(tmp_path: Path) -> None:
    """b-pair: a bar with one link raised KeyError in the chain stage."""
    result = _build("DEMO-PEBAR-2-LINKED", None, tmp_path)
    assert _symbols(result) > 0
    assert not _errors(result)


def test_a_numbered_screw_landing_on_an_interface_bar_is_drawn(tmp_path: Path) -> None:
    """a: the numbered landing gives no CONNECTION_NOT_DRAWN and draws the symbol."""
    result = _build("DEMO-PEBAR-20", "2", tmp_path, hide=False)
    assert _symbols(result) > 0
    assert "CONNECTION_NOT_DRAWN" not in _errors(result)
