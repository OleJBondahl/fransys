"""Field case UNUSED-ACCESSORY (A): `unused=` on a device inside a unit that is no boundary.

The engineering shape: a unit holds a board, and on the board a part with a footprint whose
pins the unit leaves open on purpose. The part is no field of the unit's interface, so
`unused=` once found nothing to declare: the build raised an INFO UNCONNECTED_PIN per pin.

The rule (author-0066, designer ruling 18): `unused=True` or `unused=(names,)` on any device
declares those functions open on purpose. The pins raise no UNCONNECTED_PIN and the device does
not become a boundary field. A function declared unused that is wired anyway gives
UNUSED_CONTRADICTED, which no longer reads "the boundary of no unit".
"""

from typing import Any, NamedTuple

import fransys as fr


class _Io(NamedTuple):
    pass


def _sense(*, unused: bool, wired: bool) -> Any:
    @fr.unit("demo-sense", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: Any) -> _Io:
        board = u.device("A1", "DEMO-PCB-IO")
        holder = u.device("F1", "DEMO-FUSE-HOLDER-PCB", parent=board, unused=unused)
        if wired:
            lamp = u.device("H1", "DEMO-LAMP-24")
            u.detail.wire(holder["1"], lamp["1"], wire=("RD", 50))
        return _Io()

    d = fr.design("demo_parts")
    d.add(unit, "U1")
    d.device("H9", "DEMO-LAMP-24")  # outside the unit: the unit is not standalone
    return fr.build(d)


def _codes(result: Any) -> list[str]:
    return [f.code for f in fr.check(result)]


def test_the_open_pins_of_an_internal_device_are_declared_quiet() -> None:
    result = _sense(unused=False, wired=False)
    assert _codes(result).count("UNCONNECTED_PIN") == 2  # the control: both pins fire
    quiet = _sense(unused=True, wired=False)
    assert "UNCONNECTED_PIN" not in _codes(quiet)
    assert len(fr.derive.boundaries(quiet.model)) == 0  # the device is no boundary field


def test_a_function_declared_unused_but_wired_is_contradicted() -> None:
    result = _sense(unused=True, wired=True)
    assert _codes(result).count("UNUSED_CONTRADICTED") == 1
    assert "UNUSED_CONTRADICTED" not in _codes(_sense(unused=False, wired=True))
