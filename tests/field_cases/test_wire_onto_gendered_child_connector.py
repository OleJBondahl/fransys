"""Field case: a container wires straight onto a nested unit's boundary connector.
The bug: neither wire was reported at authoring time; the direct wire onto the header surfaced only as `CONNECTION_NOT_DRAWN`.
Fixed by model-0116 (model validator, WARNING): a male or female gender takes a plug; a neutral or unstated gender takes the wire."""

from typing import Any, NamedTuple, TypedDict

import fransys as fr
import pytest
from fransys.colours import BU


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


class _Header(NamedTuple):
    X1: Any


class _Terminal(NamedTuple):
    X2: Any


_CODE = "CONNECTOR_WIRED_WITHOUT_MATE"


class _Release(TypedDict):
    revision: int
    interface_version: int
    date: str
    text: str
    by: str


_REL: _Release = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-10-01",
    "text": "First release",
    "by": "XX",
}


@fr.unit("demo-header-board", **_REL)
def _header_board(d: fr.Design) -> _Header:
    """A nested board unit whose boundary is a male pin header, `X1`."""
    board = d.device(None, "DEMO-PCB-IO", name="board")
    return _Header(d.device("X1", "DEMO-CONN-2P", parent=board, interface=True))


@fr.unit("demo-terminal-board", **_REL)
def _terminal_board(d: fr.Design) -> _Terminal:
    """A nested board unit whose boundary is a screw terminal with no gender."""
    return _Terminal(d.terminal_strip("X2", "DEMO-TB-2.5", 1, interface=True))


@fr.unit("demo-cabinet", **_REL)
def _cabinet(d: fr.Design) -> _Open:
    """A cabinet that wires onto both nested boundaries directly."""
    header = d.add(_header_board, "HDR")
    terminal = d.add(_terminal_board, "TRM")
    feed = d.terminal_strip("X9", "DEMO-TB-2.5", 2)
    d.series(feed[1].outer, header.X1[1], wire=(BU, 0.5))
    d.series(feed[2].outer, terminal.X2[1].outer, wire=(BU, 0.5))
    lead = d.terminal_strip("X8", "DEMO-TB-2.5", 1)
    d.cable("W1", "DEMO-CBL-4G1.5").core(1, lead[1].outer, header.X1[2])
    return _Open()


@pytest.fixture(scope="module")
def findings() -> tuple[fr.Finding, ...]:
    """One build of a cabinet that wires onto both nested boundaries directly."""
    d = fr.design("demo_parts")
    d.add(_cabinet, "CAB")
    return fr.check(fr.build(d))


def test_wire_onto_a_male_header_warns(findings: tuple[fr.Finding, ...]) -> None:
    fired = [f for f in findings if f.code == _CODE and "-CAB-HDR-X1" in f.message]
    assert len(fired) == 1
    assert fired[0].severity is fr.Severity.WARNING
    assert "cable's cores at the connector's pins, with no mate" in fired[0].message
    assert "mate it" not in fired[0].message


def test_a_cable_core_onto_the_male_header_is_silent(findings: tuple[fr.Finding, ...]) -> None:
    """R1260: in 0.22 a cable core on a gendered connector gives no warning; the bare wire on pin 1 still does."""
    fired = [f for f in findings if f.code == _CODE and "-CAB-HDR-X1" in f.message]
    assert len(fired) == 1
    assert "-CAB-X9:1" in fired[0].message
    assert not [f for f in findings if f.code == _CODE and "-CAB-X8" in f.message]


def test_wire_onto_a_neutral_terminal_is_silent(findings: tuple[fr.Finding, ...]) -> None:
    fired = [f for f in findings if f.code == _CODE]
    assert fired  # the header's warning is there, so the terminal's silence is told apart
    assert not [f for f in fired if "-CAB-TRM-" in f.message]


def test_the_wire_subject_prints_as_its_ends_and_never_as_a_key(
    findings: tuple[fr.Finding, ...],
) -> None:
    (fired,) = (f for f in findings if f.code == _CODE and "-CAB-HDR-X1" in f.message)
    assert "subject: wire -CAB-X9:1 to -CAB-HDR-X1:1 (" in fired.message
    assert "/wire/" not in fired.message
