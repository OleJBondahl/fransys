"""authoring.md's channel example takes channels 1 to 16; its fixed twin builds the same list."""

import re
from importlib.resources import files

import fransys as fr
from fransys.colours import BU

_SECTION = re.compile(r"## How channels are numbered\n(.*?)\n## ", re.DOTALL)
_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _list(design: fr.Design) -> list[tuple[str, str | None]]:
    return [(r.pin, r.signal_name) for r in fr.derive.plc_channel_rows(fr.build(design).model)]


def _worked_example() -> fr.Design:
    page = files("fransys").joinpath("guide/authoring.md").read_text(encoding="utf-8")
    section = _SECTION.search(page)
    assert section is not None
    scope: dict[str, object] = {}
    block = _BLOCK.search(section.group(1))
    assert block is not None
    exec(block.group(1), scope)  # noqa: S102 -- the guide's own example
    return scope["d"]  # ty: ignore[invalid-return-type] -- the block names its design d


def _fixed_twin() -> fr.Design:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    a1 = d.device("A1", "DEMO-PLC-DI-16")
    for number in range(1, 17):
        sensor = d.device(f"S{number}", "DEMO-PB-NC")
        sensor.sw.plc(fr.DI, f"Sensor {number}")
        d.series(dc.plus, sensor.sw, getattr(a1, f"di_{number}"), wire=(BU, 0.75))
    return d


def test_the_guide_example_takes_channels_one_to_sixteen_in_io_list_order() -> None:
    named = {name: pin for pin, name in _list(_worked_example()) if name}
    assert named == {f"Sensor {n}": f"-A1:{n}" for n in range(1, 17)}


def test_the_guide_example_and_its_fixed_twin_build_equal_plc_lists() -> None:
    assert _list(_worked_example()) == _list(_fixed_twin())
