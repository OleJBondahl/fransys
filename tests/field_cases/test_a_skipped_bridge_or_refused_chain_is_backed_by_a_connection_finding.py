"""Field case: a bridge (NOT_SERIES_PARALLEL) leaves a CONNECTION_NOT_DRAWN; a ring of boxes (CHAIN_REFUSED) is drawn whole.
The rule (R1013, NO-SILENT-DROP): a notice about a wiring left undrawn is backed by a finding that names the undrawn ports.
That CONNECTION_NOT_DRAWN as an ERROR makes `fr.write` refuse is proved in packages/fransys/tests/test_write_refuses_on_connection_not_drawn.py."""

from itertools import pairwise
lazy from collections.abc import Callable, Mapping, Sequence
lazy from pathlib import Path

import fransys as fr
import fransys_el.drawn_sweep
from _drawn_pages import drawn_pages
from fransys.colours import BN, BU, GN, WH, YE
lazy import pytest

from fransys_model.vocab.tables import conductors

COMMS = ((GN, 0.5), (WH, 0.5), (BN, 0.5), (YE, 0.5))


def _bridge(cover: Path) -> fr.BuildResult:
    """A Wheatstone shape: S4 joins the middles of S2-S5 and S3-S6, all into H1 and back to S1."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        s = {n: d.device(f"S{n}", "DEMO-PB-NO").sw for n in "123456"}
        h1 = d.device("H1", "DEMO-LAMP-24").lamp
        for a, b in (("1", "2"), ("1", "3"), ("2", "4"), ("2", "5"), ("4", "3"), ("3", "6")):
            d.series(s[a]["B"], s[b]["A"], wire=(BU, 0.5))
        for a in ("5", "6"):
            d.series(s[a]["B"], h1["1"], wire=(BU, 0.5))
        d.series(h1["2"], s["1"]["A"], wire=(BU, 0.5))
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _ring(cover: Path) -> fr.BuildResult:
    """Three comms modules, each wired to the next, the last back to the first, and one strip feeding the first: a ring of boxes."""
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("STRING", "Ring"):
        mods = [d.device(f"G{k}", "DEMO-MODULE-COM44") for k in (1, 2, 3)]
        for lower, upper in pairwise([*mods, mods[0]]):
            d.series(lower.comms.pins[4:], upper.comms.pins[:4], wire=COMMS)
    with d.function("JB", "Junction"):
        x2 = d.terminal_strip("X2", None, 3, external=True)
        d.series((x2[1].outer, x2[2].outer, x2[3].outer), mods[0].comms.pins[:3], wire=COMMS[:3])
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _result(built: Callable[[Path], fr.BuildResult], tmp_path: Path) -> fr.BuildResult:
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    return built(cover)


def _find(parent: dict[tuple[int, int], tuple[int, int]], at: tuple[int, int]) -> tuple[int, int]:
    while parent.setdefault(at, at) != at:
        at = parent[at]
    return at


def _drawn_ports(result: fr.BuildResult, placed: Mapping[str, Sequence[tuple[object, tuple[int, int]]]]) -> list[set[str]]:
    """The ports each connected piece of drawn ink reaches: wires joined at shared points and where an end stands on another wire.

    Each port stands where the drawn netlist placed it; the joining is this test's own, over the page wires.
    """
    pieces: list[set[str]] = []
    for page, drawing in drawn_pages(result.model).items():
        parent: dict[tuple[int, int], tuple[int, int]] = {}

        edges = [(a, b) for wire in drawing.wires for a, b in zip(wire.points, wire.points[1:], strict=False)]
        for a, b in edges:
            parent[_find(parent, a)] = _find(parent, b)
        ports = {port: at for port, spots in placed.items() for where, at in spots if where == page}
        for at in {*ports.values(), *(p for e in edges for p in e)}:
            for a, b in edges:
                if min(a[0], b[0]) <= at[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= at[1] <= max(a[1], b[1]):
                    parent[_find(parent, at)] = _find(parent, a)
        roots: dict[tuple[int, int], set[str]] = {}
        for port, at in ports.items():
            roots.setdefault(_find(parent, at), set()).add(port)
        pieces.extend(roots.values())
    return pieces


def test_every_conductor_of_a_bridge_is_drawn_or_named_by_a_connection_not_drawn(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1050: a NOT_SERIES_PARALLEL notice stays INFO; each conductor of the bridge is reached by drawn ink or a CONNECTION_NOT_DRAWN names it."""
    seen = {}
    sweep = fransys_el.drawn_sweep.dangling_findings
    monkeypatch.setattr(fransys_el.drawn_sweep, "dangling_findings", lambda net: (seen.update(net=net), sweep(net))[1])
    result = _result(_bridge, tmp_path)
    assert {f.severity for f in result.findings if f.code == "NOT_SERIES_PARALLEL"} == {fr.Severity.INFO}
    named = {port.value for f in result.findings if f.code == "CONNECTION_NOT_DRAWN" for port in f.subjects}
    drawn = _drawn_ports(result, seen["net"].placed)
    bare = [
        c.key
        for c in conductors(result.model).values()
        if not any({c.a.value, c.b.value} <= piece for piece in drawn) and not {c.a.value, c.b.value} & named
    ]
    assert not bare


def test_a_ring_of_boxes_is_drawn_whole(tmp_path) -> None:
    """R1349: a CHAIN_REFUSED ring stays INFO and leaves no CONNECTION_NOT_DRAWN, no dangling wire end: the row-wrapped hops are routed."""
    result = _result(_ring, tmp_path)
    assert {f.severity for f in result.findings if f.code == "CHAIN_REFUSED"} == {fr.Severity.INFO}  # a by-design notice (0454)
    assert not {f.code for f in result.findings} & {"CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END", "WIRE_MEETS_NET"}
    assert len(conductors(result.model)) == 15  # twelve ring hops and three strip conductors: all of them are there to be drawn
