"""Field case: a unit holds a seven-terminal interface strip and a 16-channel input module, inside a container that lands cores on the strip.
The bug: with the cores landed the unit's CABINET_SCHEMATIC gave CONNECTION_NOT_DRAWN at the last channel and terminal.
Fixed by layout-0272, a contained unit's schematic routes when the container lands cores on its interface terminals."""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import WH

N = 7


class _Out(NamedTuple):
    T: fr.TerminalStrip


@fr.unit(
    "U1",
    version=1,
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="First",
    by="XX",
    title="Unit",
    number="R-1",
)
def _u1(d: fr.Design) -> _Out:
    t = d.terminal_strip("T", "DEMO-TB-2.5", N, interface=True)
    di = d.device("DI", "DEMO-PLC-DI-16")
    for n in range(1, N + 1):
        d.series(getattr(di, f"di_{n}"), t[n], wire=(WH, 0.5))
    return _Out(t)


def _findings(d: fr.Design, root: Path, *rooms: object) -> list[fr.Finding]:
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    docs = [fr.document(preset, _u1.name, cover=root / "c.md")]
    docs += [fr.document(preset, room, cover=root / "c.md") for room in rooms]
    return list(fr.build(d, *docs).findings)


def _errors(d: fr.Design, root: Path, *rooms: object) -> list[str]:
    found = _findings(d, root, *rooms)
    return [f"{f.code}: {f.message}" for f in found if f.severity == fr.Severity.ERROR]


def _container() -> tuple[fr.Design, object]:
    """The container and its room, whose document prints the external device and the cables."""
    d = fr.design("demo_parts", place="ROOM")
    room = d.location("ROOM", "Room")
    u = d.add(_u1, "U1")
    ext = d.device("EXT", None, external=True, pins=tuple(str(n) for n in range(1, N + 1)))
    for k in range(0, N, 4):  # the demo cable has 4 cores
        w = d.cable(f"W{k // 4 + 1}", "DEMO-CBL-4G1.5", external=True)
        for core, n in enumerate(range(k + 1, min(k + 4, N) + 1), start=1):
            w.core(core, ext[str(n)], u.T[n])
    return d, room


def _container_args(root: Path) -> tuple[fr.Design, Path, object]:
    d, room = _container()
    return d, root, room


def test_the_unit_alone_builds(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_u1, "U1")
    assert _errors(d, tmp_path) == []


def test_the_unit_in_a_container_builds(tmp_path: Path) -> None:
    assert _errors(*_container_args(tmp_path)) == []


def test_the_wire_crossing_a_held_label_is_reported(tmp_path: Path) -> None:
    """layout-0272: the wire from DI 7 to terminal 7 has no clean room, so it crosses the held
    label of terminal 5 as the last resort, and WIRE_OVER_LABEL names the wire and the label."""
    crossed = [f.message for f in _findings(*_container_args(tmp_path)) if f.code == "WIRE_OVER_LABEL"]
    assert crossed
    assert all("-U1-DI:7, -U1-T:7" in message for message in crossed)
    assert any("U1-5:terminal" in message for message in crossed)
