"""Field case: a harness line whose far end stands below the content box on an overfull page.

The engineering shape: a board unit offers six headers. Four harnesses share one drawing page:
a loom with a plug on the first header and plugs on two contactors' lead housings, a loom whose
plug on a second header runs to a four-pin sensor, a loom to a two-pin device, and a loom whose
plug on the last header runs to three two-pin headers.

The bug: the page grows taller than the content box (PAGE_OVERFULL, a warning: nothing is scaled)
and the sensor stands below it. The line to the sensor is searched inside the content box, so its
fan-out split has no path and the build raised "no orthogonal path for harness line branch 1".
One contactor, or any one loom left out, kept the page inside the box and built.
The fix (decision layout-0166): a line no path in the content box can draw is searched over the box
grown to hold its ends, so the line draws and the overfull page is reported by its findings.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts

from fransys_model.kernel import merge
from fransys_model.layout import HarnessLine, layout_of

_PART = """schema = 1

[part]
mpn = "{mpn}"
manufacturer = "Demo"
description = "{mpn}"
category = "connector"
class_code = "J"

[[function]]
name = "x"
kind = "connector"
symbol = "connector-fixed"
ports = [{ports}]

[function.connector]
style = "{style}"
pincount = {n}
gender = "{gender}"
"""
_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_SENSOR = """schema = 1

[part]
mpn = "FLD-SNR4"
manufacturer = "Demo"
description = "Sensor with four pins"
category = "generic"
class_code = "B"

[[function]]
name = "s"
kind = "sensor"
ports = [
    { name = "1", role = "generic" },
    { name = "2", role = "generic" },
    { name = "3", role = "generic" },
    { name = "4", role = "generic" },
]
"""
_SENSOR2 = (
    _SENSOR.replace("SNR4", "SNR2")
    .replace("four", "two")
    .replace(', { name = "3", role = "generic" }, { name = "4", role = "generic" }', "")
)
_CONTACTOR = """schema = 1

[part]
mpn = "FLD-CTR"
manufacturer = "Demo"
description = "Contactor with coil and auxiliary contact"
category = "electromechanical"
class_code = "Q"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "X1", role = "generic", symbol_port = "in" },
    { name = "X2", role = "generic", symbol_port = "out" },
]

[[function]]
name = "aux"
kind = "contact_no"
symbol = "make-contact"
ports = [
    { name = "T1", role = "generic", symbol_port = "in" },
    { name = "T2", role = "generic", symbol_port = "out" },
]
links = [{ a = "T1", b = "T2", kind = "switched" }]
"""
_HEADERS = ("FLD-HDR-14", "FLD-HDR-4", "FLD-HDR-2", "FLD-HDR-10", "FLD-HDR-6", "FLD-HDR-10")
WIRE = ("WH", 0.5)


def _part(mpn: str, n: int, gender: str) -> str:
    ports = ", ".join(
        f'{{ name = "{i}", role = "generic", symbol_port = "{"in" if i % 2 else "out"}" }}'
        for i in range(1, n + 1)
    )
    return _PART.format(mpn=mpn, ports=ports, style=f"{mpn.lower()}-{n}p", n=n, gender=gender)


def _library(root: Path) -> Path:
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    for n in (2, 4, 6, 10, 14):
        (root / "parts" / f"hdr-{n}.toml").write_text(_part(f"FLD-HDR-{n}", n, "male"))
    for n in (2, 4, 10, 14):
        (root / "parts" / f"plg-{n}.toml").write_text(_part(f"FLD-PLG-{n}", n, "female"))
    housing = _part("FLD-HSG-4M", 4, "male")
    (root / "parts" / "hsg.toml").write_text(
        housing.replace('gender = "male"', 'gender = "male"\nmates = ["FLD-PLG-4"]')
    )
    (root / "parts" / "ctr.toml").write_text(_CONTACTOR)
    (root / "parts" / "snr.toml").write_text(_SENSOR)
    (root / "parts" / "snr2.toml").write_text(_SENSOR2)
    return root


class _Board(NamedTuple):
    j1: fr.Device
    j2: fr.Device
    j3: fr.Device
    j4: fr.Device
    j5: fr.Device
    j6: fr.Device


@fr.unit("fld-board", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
def _board(u: Any) -> _Board:
    return _Board(*(u.device(f"J{i + 1}", h, interface=True) for i, h in enumerate(_HEADERS)))


class _Top(NamedTuple):
    pass


def _contactors(u: Any, board: _Board, count: int) -> None:
    loom = u.harness("W1")
    plug = u.device("J1", "FLD-PLG-14", parent=loom, name="p1")
    u.mate(plug, board.j1)
    for i in range(count):
        q = u.device(f"Q{i + 1}", "FLD-CTR")
        housing = u.device(
            "J1",
            "FLD-HSG-4M",
            parent=q,
            name=f"h{i}",
            joins={"1": q.coil["X1"], "2": q.coil["X2"], "3": q.aux["T1"], "4": q.aux["T2"]},
        )
        lead = u.device(f"J{i + 2}", "FLD-PLG-4", parent=loom, name=f"lp{i}")
        u.mate(lead, housing)
        for pin in range(1, 5):
            u.wire(plug[str(4 * i + pin)], lead[str(pin)], wire=WIRE)


def _looms(u: Any, board: _Board) -> None:
    sensor_loom = u.harness("S1")
    sensor_plug = u.device("J1", "FLD-PLG-4", parent=sensor_loom, name="sp")
    u.mate(sensor_plug, board.j2)
    sensor = u.device("B1", "FLD-SNR4", parent=sensor_loom)
    for pin in "1234":
        u.wire(sensor_plug[pin], sensor[pin], wire=WIRE)
    pair_loom = u.harness("M1")
    pair_plug = u.device("J1", "FLD-PLG-2", parent=pair_loom, name="mp")
    u.mate(pair_plug, u.device("E1", "FLD-HDR-2"))
    pair = u.device("B2", "FLD-SNR2", parent=pair_loom)
    for pin in "12":
        u.wire(pair[pin], pair_plug[pin], wire=WIRE)
    strip_loom = u.harness("T1")
    strip_plug = u.device("J1", "FLD-PLG-10", parent=strip_loom, name="tp")
    u.mate(strip_plug, board.j6)
    for k, name in enumerate("ABC"):
        far = u.device(f"X{name}", "FLD-HDR-2")
        u.wire(strip_plug[str(2 * k + 1)], far["1"], wire=WIRE)
        u.wire(strip_plug[str(2 * k + 2)], far["2"], wire=WIRE)


def _top_with(contactors: int) -> Any:
    @fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def top(u: Any) -> _Top:
        board = u.add(_board, "A1", unused=("j3", "j4", "j5"))
        _contactors(u, board, contactors)
        _looms(u, board)
        return _Top()

    return top


@cache
def _built(contactors: int) -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(_top_with(contactors), "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    return fr.build(d, doc)


def _errors(built: fr.BuildResult) -> list[str]:
    return [f.code for f in built.findings if f.severity.name == "ERROR"]


def test_one_contactor_builds() -> None:
    assert _errors(_built(1)) == []


def test_two_contactors_build_and_the_four_looms_each_draw_a_line() -> None:
    built = _built(2)
    assert _errors(built) == []
    assert len({line.harness for line in layout_of(built.model, HarnessLine).values()}) == 4


def test_the_overfull_page_is_still_reported() -> None:
    codes = {f.code for f in _built(2).findings}
    assert "OUT_OF_CONTENT_BOX" in codes
