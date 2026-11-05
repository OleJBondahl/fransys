"""Field case: a container's own strip wired to a pin in a nested unit lands on its outer side (R1507, N7).
The bug: an end hop on a strip the container owns took its side from its place in the series, ignoring the other end's unit.
Fixed by designer R1764, `_entered` reads the other end's unit; the same-unit hop keeps the inner side."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

_FUSE = "DEMO-TB-FUSE-2.5"


class _Io(NamedTuple):
    lamp: Any


@fr.unit("demo-load", revision=1, interface_version=1, date="2026-11-05", text="1", by="AB")
def _load_unit(d: fr.Design) -> _Io:
    return _Io(d.device("H1", "DEMO-LAMP-24", interface=True))


def _terminal_side(result: fr.BuildResult) -> str:
    model = result.model
    conductors: list[Any] = list(model.tables["conductor"].values())
    keys = [model.key_of(p) or () for c in conductors for p in (c.a, c.b)]
    (side,) = {key[-1] for key in keys if "terminal" in key}
    return side


@pytest.mark.parametrize("strip_first", [True, False])
def test_a_container_strip_wired_to_a_nested_unit_lands_outer(*, strip_first: bool) -> None:
    d = fr.design("demo_parts", place="C1")
    x1 = d.terminal_strip("X1", _FUSE, 2)
    lamp = d.add(_load_unit, "U2").lamp
    pin = lamp["1"]
    d.series(*((x1[1], pin) if strip_first else (pin, x1[1])), wire=(BK, 1.5))
    d.unused(x1[2], lamp["2"])
    assert _terminal_side(fr.build(d)) == "external"


def test_a_container_strip_wired_to_a_pin_of_its_own_unit_lands_inner() -> None:
    d = fr.design("demo_parts", place="C1")
    x1 = d.terminal_strip("X1", _FUSE, 2)
    h0 = d.device("H0", "DEMO-LAMP-24")
    d.series(x1[1], h0["1"], wire=(BK, 1.5))
    d.unused(x1[2], h0["2"])
    assert _terminal_side(fr.build(d)) == "internal"
