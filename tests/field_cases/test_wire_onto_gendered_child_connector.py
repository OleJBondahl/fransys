"""Field case: a container wires straight onto a nested unit's boundary connector.

Engineering shape: a cabinet unit holds a nested board unit, and the board's boundary is a
pin header (a part whose connector gender is male). The cabinet's own wire lands on a header
pin directly, with no plug and no mate in between. A pin header needs a plug, so the build
must warn `CONNECTOR_WIRED_WITHOUT_MATE`. A second nested unit's boundary is a screw terminal
with no gender; a wire onto it is the ordinary way to reach it, and the build stays silent.

The bug: neither wire was reported at authoring time. The direct wire onto the header only
surfaced later as `CONNECTION_NOT_DRAWN` at render, far from its cause.

Fixing decision: model-0116 (model validator, WARNING; a gender of male or female takes a
plug, a neutral or unstated gender takes the wire).
"""

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
    d.wire(feed[1].outer, header.X1[1], wire=(BU, 0.5))
    d.wire(feed[2].outer, terminal.X2[1].outer, wire=(BU, 0.5))
    return _Open()


@pytest.fixture(scope="module")
def findings() -> tuple[fr.Finding, ...]:
    """One build of a cabinet that wires onto both nested boundaries directly."""
    d = fr.design("demo_parts")
    d.add(_cabinet, "CAB")
    return fr.check(fr.build(d))


def test_wire_onto_a_male_header_warns(findings: tuple[fr.Finding, ...]) -> None:
    fired = [f for f in findings if f.code == _CODE and "CAB/HDR/" in f.message]
    assert len(fired) == 1
    assert fired[0].severity is fr.Severity.WARNING


def test_wire_onto_a_neutral_terminal_is_silent(findings: tuple[fr.Finding, ...]) -> None:
    fired = [f for f in findings if f.code == _CODE]
    assert fired  # the header's warning is there, so the terminal's silence is told apart
    assert not [f for f in fired if "CAB/TRM/" in f.message]
