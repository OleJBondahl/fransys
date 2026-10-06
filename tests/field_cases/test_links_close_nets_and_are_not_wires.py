"""Field case: a mount, a bus and a rail link each close their net and are not wires.

The engineering shape: an overload relay plugged onto a contactor (a mount), two terminals of a
rack that share power through the rack's internal jumper (a bus), and two terminals that bond
through their mounting rail (a rail). None is a conductor an electrician pulls.

The bug: with no link kind, an author could only draw these as wires, which put a row, a label,
a gauge and a colour in the wire list for a part of the hardware that is not a wire.

Fixing decisions: model-0118 (`ConductorKind.MOUNT` and `RAIL` beside `BUSBAR`; a link is a
conductor with no wire facet), author-0012 (`d.busbar`, `d.rail_bond` and `mounted_on=`).
"""

import csv
import io

import fransys as fr
from fransys.colours import BK

from fransys_model.derive import net_of
from fransys_model.vocab import ConductorKind
from fransys_model.vocab.tables import conductors

_TERMINAL = "DEMO-TB-2.5"
_WIRE_LABEL = "W1"
_LINKS = (ConductorKind.MOUNT, ConductorKind.BUSBAR, ConductorKind.RAIL)


def _build() -> fr.BuildResult:
    """One contactor, its overload mounted on it, four terminals and one real wire (label `W1`)."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", _TERMINAL)
    with d.function("G", "Group"):
        contactor = d.device("Q1", "DEMO-CTR-3P-24")
        d.device("F1", "DEMO-OVERLOAD-3P", mounted_on=contactor)
        t = [strip[i] for i in range(1, 5)]
    d.busbar(t[0], t[1])
    d.rail_bond(t[2], t[3])
    d.wire(contactor.main["1"], t[0].outer, wire=(BK, 1.5), label=_WIRE_LABEL)
    return fr.build(d)


def test_each_link_closes_its_net_and_the_wire_list_has_no_row_for_it(tmp_path) -> None:
    result = _build()
    links = [c for c in conductors(result.model).values() if c.kind in _LINKS]
    assert {c.kind for c in links} == set(_LINKS)
    for link in links:
        assert net_of(result.model, link.a) == net_of(result.model, link.b), link.kind
    written = fr.write(result, tmp_path / "out")
    (path,) = (p for p in written if p.name.endswith("wires.csv"))
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    assert [row["label"] for row in rows] == ["-X1:1 -Q1:1"]  # the ends text, not the authored W1
