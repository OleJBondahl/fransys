"""Field case: a strip terminal and a relay contact pin on one page, facing each other's way.

The engineering shape: ten small circuits in one unit, each a relay whose contact takes its
feed from one of five terminals of a shared strip and whose coil is fed from another strip. The
first five circuits fill a page; the next five reuse the same five terminals, so a terminal is
drawn on the second page too, in the boundary row. On the first page the terminal stands in
its own column and a contact stands in another: the terminal's pin leaves southward, the
contact's pin northward. The two ends are one wire between neighbours, not a turn round a device.

The bug: that pair was drawn as two flags on one page (a star reference with a single branch)
and no wire, because a join across columns was only decided for ends facing one way, and an
opposite-facing pair was neither joined nor reported.
The rule (decision layout-0180; layout-0093 M12, ruling 2026-09-23): markers belong at circuit
ends, a short wire between ends on one page is allowed, and only a 180 degree route round a device
is refused. Ends of one page that face each other's way and do not turn back are a plain wire.
"""

import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BK, BU, RD

from fransys_model.derive import net_of
from fransys_model.layout import LinkMarker, StarKind, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port

_CIRCUITS = 10
_BUS = 5


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit(
    "shape",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Shape",
    number="S-1",
)
def _shape(d: fr.Design) -> _Io:
    """Ten relay circuits on two shared strips, five terminals reused."""
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 8)
    for i in range(_CIRCUITS):
        with d.function(f"C{i + 1:02d}", f"Circuit {i + 1}"):
            k = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            h = d.device(f"H{i + 1}", "DEMO-LAMP-24")
            d.detail.wire(x1[1 + i % _BUS], k.coil["A1"], wire=(RD, 0.75))
            d.detail.wire(x1[8], k.coil["A2"], wire=(BK, 0.75))
            d.detail.wire(x2[1 + i % _BUS], k.co_1["11"], wire=(RD, 0.75))
            d.detail.wire(k.co_1["14"], h.lamp[1], wire=(RD, 0.75))
            d.detail.wire(h.lamp[2], x2[8], wire=(BU, 0.75))
    return _Io(x1)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """The shape above, built once as a cabinet document."""
    d = fr.design("demo_parts")
    d.add(_shape, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Shape\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "shape", cover=cover))


def _pin(result: fr.BuildResult, circuit: str) -> Id[Port]:
    """Pin 11 of the relay of `circuit` (`C02`): the contact fed from the strip."""
    model = result.model
    (found,) = (
        port.id
        for port in model.tables["port"].values()
        if (key := model.key_of(port.id)) is not None
        and key[-1] == "11"
        and key[1].startswith(circuit)
    )
    return found


def _lone_branches(result: fr.BuildResult) -> int:
    """The pages' star references that show exactly one branch: a pair in all but name."""
    model = result.model
    shown = defaultdict(list)
    for marker in layout_of(model, LinkMarker).values():
        net = net_of(model, marker.port)
        if marker.star is not None and net is not None:
            shown[marker.page, net.ports].append(marker.star)
    return sum(
        stars.count(StarKind.BRANCH) == 1 and StarKind.REF in stars for stars in shown.values()
    )


def test_a_reference_never_shows_a_single_branch_on_one_page(built: fr.BuildResult) -> None:
    """The pair of ends on one page is a wire, so no page shows a reference with one branch."""
    assert _lone_branches(built) == 0


def _wired_contacts(result: fr.BuildResult, tag: str) -> list[object]:
    """The pin-11 contact symbols whose nearest tag is `tag` and that a drawn wire ends at."""
    found = []
    for drawing in drawn_pages(result.model).values():
        ends = {point for wire in drawing.wires for point in (wire.points[0], wire.points[-1])}
        tags = [t for t in drawing.texts if t.kind == "TAG"]
        for symbol in drawing.symbols:
            if ("marking.in", "11") not in symbol.slots or not tags:
                continue
            near = min(tags, key=lambda t: abs(t.box.x - symbol.x) + abs(t.box.y - symbol.y))
            if near.text.endswith(f"-{tag}") and any(
                abs(x - symbol.x) + abs(y - symbol.y) <= 24 for x, y in ends
            ):
                found.append(symbol)
    return found


def test_the_second_contact_is_wired_to_its_terminal_not_flagged(built: fr.BuildResult) -> None:
    """Contact 11 of circuit 2 stands beside a copy of its terminal: a route, no marker."""
    pin = _pin(built, "C02")
    assert pin not in {m.port for m in layout_of(built.model, LinkMarker).values()}
    assert _wired_contacts(built, "K2")
