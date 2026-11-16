"""Field case: a mount and a bus link each close their net and are not wires.
The bug: with no link kind these were drawn as wires; a busbar to a boundary receptacle drew none (LANE_WIRE_DROPPED, KI-1067).
Fixed by model-0118 (ConductorKind.MOUNT beside BUSBAR), author-0012 (d.busbar, mounted_on=) and model-0472 (KI-1067)."""

import csv
import io
from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
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


class _Io(NamedTuple):
    plug: fr.Device


def _board(plugs: int, cover: Path) -> fr.BuildResult:
    """A unit of `plugs` boundary receptacles, each busbarred to the first pin of a fuse whose second pin is busbarred to a second receptacle."""

    @fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="demo", by="XX")
    def board(d: fr.Design) -> _Io:
        plugs_made = [d.device(None, "BUSBAR-RECEPT", name=f"plug{n}", interface=True) for n in range(1, plugs + 1)]
        for n, plug in enumerate(plugs_made, 1):
            fuse = d.device(f"F{n}", "DEMO-FUSE-ABAT")
            d.detail.busbar(plug.main["internal"], fuse.element["1"])
            d.detail.busbar(fuse.element["2"], d.device(None, "BUSBAR-RECEPT", name=f"lug{n}").main["internal"])
        return _Io(plugs_made[0])

    d = fr.design("demo_parts", "busbar_parts")
    d.add(board, "U1")
    return fr.build(d, fr.document(fr.DocumentPreset("cabinet_schematic"), "demo-board", cover=cover))


@pytest.mark.parametrize("plugs", [1, 3])
def test_a_busbar_between_a_boundary_receptacle_and_a_fuse_draws_its_wire(plugs: int, tmp_path: Path) -> None:
    (tmp_path / "c.md").write_text("# Demo\n", encoding="utf-8")
    result = _board(plugs, tmp_path / "c.md")
    assert [f.code for f in result.findings if f.severity is fr.Severity.ERROR] == []
    assert sum(len(page.wires) for page in drawn_pages(result.model).values()) >= 2 * plugs
