"""The author's unit boundary terminals against the model's `unit_boundary_pins` (design 7.3).

The author's side is the pins of the devices a unit's function returns; the model's side is the
pins of the functions its `Boundary` records name. A nested unit's pass-through counts in both.
"""

from typing import Any, NamedTuple

from fransys_author.surface import Design, Device, design, unit

from fransys_model.derive import unit_boundary_pins
from fransys_model.kernel import freeze, merge
from fransys_model.vocab import units

from .equivalence.series_parts import pair_library
from .surface.test_units import io_board


class _Outer(NamedTuple):
    X1: Device


_INNER: list[Any] = []


@unit("demo-outer", revision=1, interface_version=1, date="2026-02-02", text="outer", by="XX")
def outer(d: Design) -> _Outer:
    inner = d.add(io_board, "IO")
    _INNER.append(inner)
    return _Outer(inner.X1)


def _pins(*devices: Device) -> set[object]:
    return {pin.id for device in devices for _, pin in device._pins()}


def test_each_unit_lists_the_pins_the_author_returned() -> None:
    """The nested board lists both its connectors; the outer unit passes only X1 up."""
    _INNER.clear()
    d = design(pair_library())
    d.add(outer, "OU")
    model = freeze(merge(pair_library(), d.draft()))
    inner = _INNER[0]
    by_name = {("outer" if u.parent is None else "inner"): u.id for u in units(model).values()}
    assert set(unit_boundary_pins(model, by_name["inner"])) == _pins(inner.X1, inner.X2)
    assert set(unit_boundary_pins(model, by_name["outer"])) == _pins(inner.X1)
    assert len(_pins(inner.X1, inner.X2)) > len(_pins(inner.X1)) > 0
