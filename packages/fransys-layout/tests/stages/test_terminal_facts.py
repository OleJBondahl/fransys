"""The terminal facts: `inline_terminal` and `terminal_point`, one function each (layout-0113)."""

import pytest

from fransys_layout.conventions import FACTS
from fransys_layout.stages.terminal_facts import TerminalRead, inline_terminal, terminal_point


def _read(ports: int, wires: int, *, terminal: bool = True) -> TerminalRead:
    return TerminalRead(terminal=terminal, ports=ports, wires=wires)


@pytest.mark.parametrize(
    ("read", "expected"),
    [
        pytest.param(_read(1, 2), True, id="one port, two wires"),
        pytest.param(_read(1, 1), False, id="one wire is a point, not in line"),
        pytest.param(_read(1, 3), False, id="three wires"),
        pytest.param(_read(2, 2), False, id="two ports"),
        pytest.param(_read(1, 2, terminal=False), False, id="not a terminal"),
    ],
)
def test_inline_terminal(read: TerminalRead, *, expected: bool) -> None:
    """Only a one-port terminal with exactly two wires is in line."""
    assert inline_terminal(read) is expected


@pytest.mark.parametrize(
    ("read", "expected"),
    [
        pytest.param(_read(1, 1), True, id="terminal, one wire"),
        pytest.param(_read(2, 1), True, id="two-port terminal, one wire"),
        pytest.param(_read(1, 2), False, id="two wires is in line"),
        pytest.param(_read(1, 0), False, id="no wire"),
        pytest.param(_read(1, 1, terminal=False), False, id="not a terminal"),
    ],
)
def test_terminal_point(read: TerminalRead, *, expected: bool) -> None:
    """Only a terminal with exactly one wire is a lone point."""
    assert terminal_point(read) is expected


def test_both_facts_are_registered_with_their_functions() -> None:
    """The registry holds each fact by name, physical, bound to the one function."""
    assert FACTS["inline_terminal"].func is inline_terminal
    assert FACTS["terminal_point"].func is terminal_point
    assert {FACTS[n].kind for n in ("inline_terminal", "terminal_point")} == {"physical"}
