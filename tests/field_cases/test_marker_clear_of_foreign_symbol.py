"""Field case: a link marker's net runs to a strip terminal of another group, drawn here as a replica.
The bug: the placer tested the marker box against symbol bodies but not its stub, so the stub ran through a terminal's symbol.
Fixed by layout-0093 (M7 and M9), a box and its stub never stand on a wire or a symbol of another function."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import LinkMarker, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_CODES = ("WIRE_THROUGH_SYMBOL",)


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    title="Cab",
    number="X-1",
    date="2026-10-02",
    text="First release",
    by="XX",
)
def _cabinet(u: fr.Design) -> _Open:
    """A coil pair whose return leaves through a pass-through to a replica terminal."""
    u.location("C1", "Cabinet")
    strip = u.terminal_strip("X2", "DEMO-TB-2.5", place="C1")
    with u.function("FEED", "Feed"):
        terminal = strip[1]
    with u.function("LOAD", "Load"):
        contactor = u.device("K1", "DEMO-RLY-2CO-24", place="C1")
        overload = u.device("F1", "DEMO-OVERLOAD-A2", place="C1")
        relay = u.device("K2", "DEMO-RLY-2CO-24", place="C1")
    u.series(contactor.coil["A2"], overload.a2["A2"], wire=("BK2", 1.5))
    u.series(overload.a2["A2"], terminal, wire=("BK2", 1.5))
    u.series(relay.coil["A1"], contactor.coil["A1"], wire=("BK2", 1.5))
    u.series(relay.coil["A2"], contactor.coil["A2"], wire=("BK2", 1.5))
    return _Open()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    """One build of the coil pair in its unit, in a cabinet-schematic document."""
    d = fr.design("demo_parts")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.add(_cabinet, "CAB")
    cover: Path = tmp_path_factory.mktemp("cover") / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cabinet", cover=cover)
    return fr.build(d, doc)


def test_marker_stub_and_box_clear_of_foreign_symbols(built: fr.BuildResult) -> None:
    assert [f.code for f in fr.check(built) if f.code in _CODES] == []


def test_the_pass_through_carries_a_marker(built: fr.BuildResult) -> None:
    """The fixture builds the shape the docstring describes, whichever place the marker takes."""
    markers = layout_of(built.model, LinkMarker).values()
    assert [m for m in markers if "a2" in m.key and "A2" in m.key]
