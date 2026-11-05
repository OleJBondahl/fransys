"""Field case: a mate and a harness line are refused with MATES_DISABLED (R1216) and `fr.write` raises.
The plug-to-coil case (`MATE_NOT_CONNECTOR`) is deleted: its only concern was a mate, which 0.22 refuses (R1249)."""

from typing import NamedTuple
lazy from collections.abc import Callable
lazy from pathlib import Path

import fransys as fr
import pytest
from _expected_codes import expect_codes

_PLUG = "DEMO-CONN-2P"


class _Io(NamedTuple):
    X1: fr.Device
    X2: fr.Device


@fr.unit("demo-mated-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _mated_board(u: fr.Design) -> _Io:
    first, second = u.device("X1", _PLUG, interface=True), u.device("X2", _PLUG, interface=True)
    u.mate(first, second)
    return _Io(first, second)


def _design_mate(_cover: Path) -> tuple[fr.Design, tuple[fr.Draft, ...]]:
    d = fr.design("demo_parts")
    d.mate(d.device("P1", _PLUG), d.device("P2", _PLUG))
    return d, ()


def _design_unit_mate(_cover: Path) -> tuple[fr.Design, tuple[fr.Draft, ...]]:
    d = fr.design("demo_parts")
    d.add(_mated_board, "U1")
    return d, ()


def _design_harness(_cover: Path) -> tuple[fr.Design, tuple[fr.Draft, ...]]:
    d = fr.design("demo_parts")
    d.harness("W1")
    return d, ()


@pytest.mark.parametrize("make", [_design_mate, _design_unit_mate, _design_harness])
def test_write_refuses_a_mate_and_a_harness_line(make: Callable[[Path], tuple[fr.Design, tuple[fr.Draft, ...]]], tmp_path: Path) -> None:
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d, documents = make(cover)
    result = fr.build(d, *documents)
    expect_codes(result, "MATES_DISABLED")
    with pytest.raises(fr.BuildFailedError, match=r"MATES_DISABLED.*draw the connection as a cable or wires"):
        fr.write(result, tmp_path / "out")
