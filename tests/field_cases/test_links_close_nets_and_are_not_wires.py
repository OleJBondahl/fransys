"""Field case: a mount and a bus link each close their net and are not wires.
The bug: with no link kind these were drawn as wires, putting hardware rows on the wire list.
Fixed by model-0118 (ConductorKind.MOUNT beside BUSBAR) and author-0012 (d.busbar, mounted_on=)."""

import csv
import io

import fransys as fr
from fransys.colours import BK

from fransys_model.derive import net_of
from fransys_model.vocab import ConductorKind
from fransys_model.vocab.tables import conductors

_TERMINAL = "DEMO-TB-2.5"
_LINKS = (ConductorKind.MOUNT, ConductorKind.BUSBAR)


def _build() -> fr.BuildResult:
    """One contactor, its overload mounted on it, two terminals and one real wire."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", _TERMINAL)
    with d.function("G", "Group"):
        contactor = d.device("Q1", "DEMO-CTR-3P-24")
        d.device("F1", "DEMO-OVERLOAD-3P", mounted_on=contactor)
        t = [strip[i] for i in range(1, 3)]
    d.detail.busbar(t[0], t[1])
    d.series(contactor.main["1"], t[0].outer, wire=(BK, 1.5))
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
    assert [row["label"] for row in rows] == ["-X1:1 -Q1:1"]  # the ends text, not an authored label
