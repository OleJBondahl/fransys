"""layout-0221: a set's order never reaches output; the same input gives the same bytes.

An end whose ports stand in two boxed connectors on one page (the SUP/W1 stub of the pump
station) took the box its set walk met first, so its `layout.stub_end` x moved with
`PYTHONHASHSEED`. Two interpreters with different seeds must now agree on the least corner.

Run as a script, the module prints the spot; the test runs it under two seeds (about 3 s).
"""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_layout.engines.schematic.read.stub_places import end_spots
from fransys_model.derive import harness_line_ends
from fransys_model.vocab.tables import items, ports

SEEDS = ("0", "3")  # the first pair whose set order differs for the unfixed walk


class _Open(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    a = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    b = u.device("J2", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    lamp = u.device("K1", "DEMO-LAMP-24")
    u.detail.wire(a[1], lamp["1"], wire=(BK, 0.5))
    u.detail.wire(b[1], lamp["2"], wire=(BK, 0.5))
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, a[1], b[1])
    return _Open()


def _spots() -> str:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    model = fr.build(d).model
    cable = next(i.id for i in items(model).values() if i.tag == "W1")
    end = harness_line_ends(model, cable)[0]
    ends = [ports(model)[p].function for e in harness_line_ends(model, cable) for p in e.ports[:1]]
    one, other = sorted(set(ends))[:2]
    pair = replace(
        end, plug=None, ports=tuple(p for e in harness_line_ends(model, cable) for p in e.ports)
    )
    box = lambda x: SimpleNamespace(box=SimpleNamespace(x=x, y=20))  # noqa: E731  # a stand-in box
    placed: Any = {one: {(1, 2): box(90)}, other: {(1, 2): box(10)}}
    return repr(end_spots(model, pair, placed, {}, frozenset()))


def _under(seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    run = subprocess.run(  # noqa: S603 -- fixed argv: this interpreter and this file
        [sys.executable, str(Path(__file__)), "spots"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return run.stdout.strip()


def test_the_spot_of_an_end_in_two_boxes_is_the_same_under_every_hash_seed() -> None:
    spots = {seed: _under(seed) for seed in SEEDS}
    assert set(spots.values()) == {"{(1, 2): (10, 20)}"}, spots


if __name__ == "__main__":
    sys.stdout.write(_spots())
