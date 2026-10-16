"""Field case: a container released after its nested unit, over two alike devices on a strip.

The engineering shape: a unit holds one terminal strip and two devices of one part, both mounted
on the strip and differing only by name. The unit is released, then a container that nests it is
released into the same releases folder.

The bug: the container's release raised BASELINE_DIFFERS ("differs from its released baseline in:
items") though the item sets were equal. The listing sorts items on designation, part, installed,
external and position; the two devices tie on all of them, so their order followed the model's
insertion order, which differs between the unit built alone and the unit built nested.

The rule (decision model-0309): a unit's listing order is the same alone and nested; ties break
on the unit-local item key.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr


class _Io(NamedTuple):
    X1: fr.TerminalStrip


class _Empty(NamedTuple):
    pass


@fr.unit("demo-tie-u", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _inner(d: fr.Design) -> _Io:
    x = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    for n in (1, 2):
        d.device(None, "DEMO-JUMPER-BAR-3P", name=f"jumper bar L{n}", parent=x)
    return _Io(X1=x)


@fr.unit("demo-tie-c", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _outer(d: fr.Design) -> _Empty:
    d.add(_inner, "U1")
    return _Empty()


def _build(unit: Any, releases: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    return fr.build(d, releases=releases)


def test_a_container_releases_after_its_nested_unit(tmp_path: Path) -> None:
    fr.release(_build(_inner, tmp_path), tmp_path, unit="demo-tie-u")
    fr.release(_build(_outer, tmp_path), tmp_path, unit="demo-tie-c")
