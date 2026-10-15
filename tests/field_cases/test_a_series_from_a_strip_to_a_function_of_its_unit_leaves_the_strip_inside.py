"""Field case: a series from a strip to a function of the same unit leaves the strip inside.

The engineering shape: a unit with an interface strip X1 and a relay K1. A series from the strip's
run `DI` to the coil of K1 carries the run's terminal to a function in the same unit.

The bug: the series left the strip on its outer side, the field side where a homerun lands, so the
coil wire sat beside the field cable. A strip last in a series (`d.series(supply, fuse, x1)`) was
right: it is entered on its inner side.

Rule: a series that starts on a strip, and does not go on into a cable, leaves the strip on its
inner side (authoring.md, "Strips and terminals"). A strip followed by a cable leaves outer.
Decision: API-FRICTION-1 F4.
"""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BU

from fransys_model.vocab.tables import conductors, ports


class _Station(NamedTuple):
    """A unit with no boundary device to hand back."""


@fr.unit(
    "station",
    revision=1,
    interface_version=1,
    date="2026-10-15",
    text="First issue",
    by="XX",
    title="Station",
    number="S-1",
)
def _station(u):
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    run = x1.run("DI", 1)
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    u.series(run, k1.coil, wire=(BU, 0.75))
    return _Station()


def test_a_series_from_a_strip_to_a_function_of_its_unit_leaves_the_strip_inside(tmp_path) -> None:
    (tmp_path / "cover.md").write_text("# Station\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_station, "U1")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "station", cover=tmp_path / "cover.md")
    ).model
    keys = {p.id: p.key for p in ports(model).values()}
    ends = [{keys[w.a], keys[w.b]} for w in conductors(model).values()]
    (terminal_ends,) = [
        key for pair in ends for key in pair if "X1" in key and key[-1] in ("internal", "external")
    ]
    assert terminal_ends[-1] == "internal"
