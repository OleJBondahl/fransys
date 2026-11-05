"""Field case: a strip terminal drawn at a box end is wired on another page at its other connection point.
The bug: the copy at the box end draws its far pin as a bare stub, with no reference text to the copy where that pin is wired (KI-511).
Open: a strict xfail by its gap row, the owner's terminal rule is one symbol per connection point, each with reference text to the others."""

from collections import defaultdict
from typing import NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages, markers_in, ref_texts
from _model_build_cover import unit_document
from fransys.colours import BU


class _Io(NamedTuple):
    L1: fr.Run
    N: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cabinet(u: fr.Design) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        l1, n = x1.run("L1", 1), x1.run("N", 1)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.series(l1[1].inner, lamp["1"], wire=(BU, 0.5))
        u.series(lamp["2"], n[1].inner, wire=(BU, 0.5))
    return _Io(l1, n)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Stub", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    cab = d.add(_cabinet, "U1", place=None)
    with d.function("IN", "Incoming"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
        cable.core(1, x0.run("L1", 1)[1], cab.L1[1])
        cable.core(2, x0.run("N", 1)[1], cab.N[1])
    return fr.build(d, unit_document(cabinet), unit_document(cab))


def test_a_terminal_pin_wired_on_another_copy_has_reference_text_on_this_one(built: fr.BuildResult) -> None:
    """Each pin of a drawn terminal that another page's copy of it wires carries a marker with reference text."""
    pages = drawn_pages(built.model)
    seen: dict[str, set[object]] = defaultdict(set)
    for page, drawing in pages.items():
        for s in drawing.symbols:
            if s.key == "terminal":
                for port in s.ports:
                    seen[port].add(page)
    bare = [
        (page, port)
        for page, drawing in pages.items()
        for s in drawing.symbols
        if s.key == "terminal"
        for port in s.ports
        if seen[port] - {page} and not any(port in m.ports and ref_texts(m) for m in markers_in(drawing))
    ]
    assert not bare, f"{len(bare)} terminal pin(s) wired on another page's copy carry no reference text on this page: {bare}"
