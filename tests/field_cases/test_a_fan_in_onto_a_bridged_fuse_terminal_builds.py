"""Field case: two terminals of one strip wired to the outer side of a bridged fuse terminal.

The engineering shape: a cabinet unit with an interface strip X1 of fused terminals (the fuse
sits between the two connections, a `protective` link), a run of 6 on it bridged and made outside
every block, a declared DC supply in block V wired to run terminal 2, and in block G two terminals
of another interface strip X2 wired to the outer side of run terminal 6.

The bug: `fr.build` raised `KeyError` in `fransys_layout` `host_offsets._attach_at_host`. The
fused terminal's own cell was on no page of the set, but the X2 cells hung on it named it as their
host, and layout looked the host up on the page and did not find it. Dropping any one of the
fused link, `bridged`, the supply, `interface`, or the second X2 terminal made it build.

A second bug, in the same case: the wire from a flipped (turned 180 degrees) fuse terminal to the
terminals hung on it left upward and U-turned down, because the attachment read the host port's
facing from the unflipped geometry. The fix, FAN-IN-UTURN, has the attachment read the port
as drawn.

Reported by a consumer, reproduced 2026-10-14. Fixing decision: model-0215 -- a terminal with a
protective link is not a rail terminal, so it draws as a terminal and keeps its home cell.
"""

from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import BU

from fransys_model.layout import Route, layout_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from pathlib import Path


class _Cab(NamedTuple):
    """A unit with no boundary device to hand back."""


@fr.unit(
    "cab",
    revision=1,
    interface_version=1,
    date="2026-10-14",
    text="First issue",
    by="XX",
    title="Cabinet",
    number="C-1",
)
def _cab(c):
    x2 = c.terminal_strip("X2", "DEMO-TB-2.5", 4, interface=True)
    run = c.terminal_strip("X1", "DEMO-TB-FUSE-2.5", interface=True).run("24V", 6, bridged=True)
    with c.function("V", "Supply"):
        psu = c.device("G1", "DEMO-PSU-24")
        c.wire(psu.output["+"], run[2], wire=(BU, 0.75))
        c.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    with c.function("G", "Group"):
        for k in (1, 2):
            c.wire(x2[k], run[6].outer, wire=(BU, 0.75))
    return _Cab()


def test_a_fan_in_onto_a_bridged_fuse_terminal_builds(tmp_path: Path) -> None:
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=tmp_path / "cover.md")
    )
    assert result.model is not None


def _turns_back(points: list[tuple[int, int]]) -> bool:
    """True when two segments one apart run opposite ways on one axis (a U, up then down)."""
    steps = [(bx - ax, by - ay) for (ax, ay), (bx, by) in pairwise(points)]
    for first, third in zip(steps, steps[2:], strict=False):
        opposite = (first[0] * third[0] < 0 and first[1] == third[1] == 0) or (
            first[1] * third[1] < 0 and first[0] == third[0] == 0
        )
        if opposite:
            return True
    return False


def test_the_wire_from_the_fuse_terminal_reaches_the_fan_in_without_a_u_turn(
    tmp_path: Path,
) -> None:
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=tmp_path / "cover.md")
    ).model
    port_key = {p.id: p.key for p in ports(model).values()}
    routes = [
        r
        for r in layout_of(model, Route).values()
        if ("U1", "X1", "terminal", "24V", "6", "fn", "terminal", "port", "external")
        in (port_key[r.a], port_key[r.b])
    ]
    assert len(routes) == 2  # one per X2 terminal
    assert not any(_turns_back([(p.x, p.y) for p in r.points]) for r in routes)
