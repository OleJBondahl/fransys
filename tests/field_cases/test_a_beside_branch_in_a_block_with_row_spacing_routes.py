"""Field case: a branch stood beside a main chain that starts with one switch pole still routes.

The engineering shape: one function block holds a terminal pair, a two-pole switch (one pole
used), a fuse, two breakers and a resistor. The main chain runs terminal, switch pole, fuse,
breaker, terminal. A branch chain (resistor, second breaker, fuse) stands `beside=` the first
breaker, wired from that breaker's output pin to the resistor. The unit sets
`layout.profile(row_spacing=400)`.

The bug: in 0.16.0 that one wire raised ROUTE_FAILED and two CONNECTION_NOT_DRAWN. The block,
the row spacing and the switch pole are each needed; 0.15.1 built it clean.

Decision layout-0174 (ROUTE-016) fixed it: when the join's end pin finds no path, the join is
searched once more with the shallower pin.
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import RD

if TYPE_CHECKING:
    from pathlib import Path


class _Cab(NamedTuple):
    pass


def _unit(*, block: bool, spacing: int, switch: bool) -> Any:
    @fr.unit("demo-rs", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def _rs(d: Any) -> _Cab:
        if spacing:
            d.layout.profile(row_spacing=spacing)
        with d.function("B1", "Block") if block else nullcontext():
            s = d.terminal_strip("X1", "DEMO-TB-2.5")
            a, b = s.run("A", 1), s.run("B", 1)
            _ = a[1], b[1]
            sw = d.device("S1", "DEMO-MCB-2P")
            f1 = d.device("F1", "DEMO-FUSE-DC-160")
            f3 = d.device("F3", "DEMO-FUSE-DC-160")
            q1 = d.device("B1", "DEMO-MCB-2P")
            q3 = d.device("B2", "DEMO-MCB-2P")
            r1 = d.device("R5", "DEMO-LAMP-24")
        head = [(a[1], sw.pole_1["1"], 100), (sw.pole_1["2"], f1.element["1"], 100)]
        if not switch:
            head = [(a[1], f1.element["1"], 100)]
        for p, q, w in [
            *head,
            (f1.element["2"], q1.pole_1["1"], 100),
            (q1.pole_1["2"], b[1], 100),
            (q1.pole_1["2"], r1["1"], 16),
            (r1["2"], q3.pole_1["1"], 16),
            (q3.pole_1["2"], f3.element["1"], 16),
            (f3.element["2"], f1.element["2"], 16),
        ]:
            d.detail.wire(p, q, wire=(RD, w))
        first = (sw.pole_1,) if switch else ()
        d.layout.chain(a[1], *first, f1.element, q1.pole_1, b[1])
        d.layout.chain(r1.lamp, q3.pole_1, f3.element, beside=q1.pole_1)
        return _Cab()

    return _rs


def _errors(
    root: Path, *, block: bool = True, spacing: int = 400, switch: bool = True
) -> list[str]:
    d = fr.design("demo_parts")
    d.add(_unit(block=block, spacing=spacing, switch=switch), "U1")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-rs", cover=root / "c.md")
    found = fr.check(fr.build(d, doc))
    return sorted(f.code for f in found if f.severity is fr.Severity.ERROR)


def test_the_branch_beside_a_switch_pole_chain_routes(tmp_path: Path) -> None:
    assert _errors(tmp_path) == []


@pytest.mark.parametrize(
    "variant",
    [{"block": False}, {"spacing": 0}, {"switch": False}],
    ids=["no-block", "no-row-spacing", "no-switch-pole"],
)
def test_each_variant_without_one_trigger_is_clean(variant: dict[str, Any], tmp_path: Path) -> None:
    assert _errors(tmp_path, **variant) == []
