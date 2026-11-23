"""Field case: a switch pole's load pin takes two conductors, one to a strip terminal and one to a passive's pin.
The bug (KI-974, CHAIN-FROM-HEAD): the passive's wire is drawn from the terminal, joining them where no conductor runs.
Fixed by R2629: a terminal stands inline only between two ends it has conductors to."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from fransys.colours import BU
from fransys_el import lay_out_core
lazy import pytest

from fransys_model.derive import port_designation

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    x2: fr.TerminalStrip


def _design(*, landed: bool) -> fr.Design:
    @fr.unit("demo-ink", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Ink", number="I-1")
    def ink(d: fr.Design) -> _Io:
        with d.function("DC", "DC group"):
            x2 = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN", 3)
            q1 = d.device("Q1", "DEMO-SWITCH-DC-2P")
            r1 = d.device("R1", "DEMO-LAMP-24")
        d.series(q1.main[2], x2[2], wire=(BU, 0.75))
        d.series(x2[2] if landed else q1.main[2], r1[1], wire=(BU, 0.75))
        d.series(r1[2], x2[3], wire=(BU, 0.75))
        return _Io(x2)

    d = fr.design("demo_parts")
    d.location("HWR", "Room")
    d.add(ink, "U1", place="HWR")
    return d


def _build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, landed: bool) -> tuple[Any, list[Any]]:
    caught: list[Any] = []
    original = lay_out_core.drawn_netlist
    monkeypatch.setattr(lay_out_core, "drawn_netlist", lambda *a: caught.append(a) or original(*a))
    (tmp_path / "cover.md").write_text("# Ink\n", encoding="utf-8")
    result = fr.build(_design(landed=landed), fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-ink", cover=tmp_path / "cover.md"))
    return result, caught


def _runs(caught: list[Any]) -> set[frozenset[str]]:
    """The designations of each pair of ports one drawn wire joins directly."""
    model, kit, drawings, links, library = caught[-1]
    net = lay_out_core.drawn_netlist(model, kit, drawings, links, library)
    runs = set()
    for part in net.pages.values():
        at = {}
        for port, xy in part.ports.items():
            at.setdefault(xy, []).append(port_designation(model, net.ids[port]))
        runs |= {frozenset(at[a] + at[b]) for a, b in map(tuple, part.graph.edges) if a in at and b in at}
    return runs


def test_a_conductor_on_a_switch_load_pin_is_drawn_to_that_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, caught = _build(tmp_path, monkeypatch, landed=False)
    assert "INK_WITHOUT_CONDUCTOR" not in {f.code for f in fr.check(result)}
    runs = _runs(caught)
    assert not any({"-U1-R1:1", "-U1-X2:2"} <= run and "-U1-Q1:2" not in run for run in runs)


def test_control_a_conductor_on_the_terminal_is_drawn_to_the_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _build(tmp_path, monkeypatch, landed=True)
    assert "INK_WITHOUT_CONDUCTOR" not in {f.code for f in fr.check(result)}
