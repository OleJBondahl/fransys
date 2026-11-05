"""Field case UNUSED-ACCESSORY (A): a unit holds a board with a fuse-holder part whose pins the unit leaves open on purpose.
The bug: `unused=` found nothing to declare in a unit that is no boundary, so the build raised an INFO UNCONNECTED_PIN per pin.
Fixed by author-0066 (designer ruling 18), `unused=` on any device declares those pins open on purpose."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    pass


def _sense(*, unused: bool, wired: bool) -> Any:
    @fr.unit("demo-sense", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: Any) -> _Io:
        board = u.device("A1", "DEMO-PCB-IO")
        holder = u.device("F1", "DEMO-FUSE-HOLDER-PCB", parent=board, unused=unused)
        if wired:
            lamp = u.device("H1", "DEMO-LAMP-24")
            u.series(holder["1"], lamp["1"], wire=("RD", 50))
            u.series(holder["2"], lamp["2"], wire=("BU", 50))
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


def _lone_lamp(cover: Path, *, unused: bool) -> Any:
    @fr.unit("demo-lone", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: Any) -> _Io:
        u.device("H1", "DEMO-LAMP-24", unused=unused)
        h2, h3 = u.device("H2", "DEMO-LAMP-24"), u.device("H3", "DEMO-LAMP-24")
        u.series(h2["1"], h3["1"], wire=("RD", 50))  # a drawn page
        u.series(h2["2"], h3["2"], wire=("BU", 50))
        return _Io()

    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(unit, "U1", place="C1")
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-lone", cover=cover))


def test_an_unused_device_left_unwired_is_no_function_not_wired(tmp_path: Path) -> None:
    assert "FUNCTION_NOT_WIRED" in _codes(_lone_lamp(tmp_path / "a.md", unused=False))  # the control: undeclared, it warns
    assert "FUNCTION_NOT_WIRED" not in _codes(_lone_lamp(tmp_path / "b.md", unused=True))
