"""Field case: `ac_supply` refuses the pins of a fuse or breaker, naming the branch rule.

The engineering shape: a 230 V supply feeds a breaker F4, and a second breaker F8 is fed from F4's
line screws. The author declares a supply on F4's pins to start the branch from it.

The bug: the call was accepted, so F4's pins became a second source of the same voltage and the
branch started on rails that no source feeds ("a fused branch is not a supply" in the guide).

Decision author-0055 (API-FRICTION-2 R4): `ac_supply` refuses a pin of a protective function and
names the rule. A branch from the common feed is a second series from that feed; a branch looped at
the line screws is wired with `d.detail.wire`, one hop per pole, until a series can start at a named
pin (API-FRICTION-2 C6). A device with no protective function, such as a power supply's input,
still declares a supply.
"""

import fransys as fr
import pytest
from fransys.colours import BK
from fransys_author import AuthorError


def test_a_breakers_pins_are_refused_with_the_branch_rule() -> None:
    d = fr.design("demo_parts")
    f4 = d.device("F4", "DEMO-MCB-3P")
    with pytest.raises(AuthorError, match=r"a fused branch is not a supply") as raised:
        d.ac_supply("BRANCH", 230, f4.element["1"], f4.element["3"], f4.element["5"])
    assert "F4" in str(raised.value)
    assert "second series" in str(raised.value)


def test_the_neutral_pin_of_a_breaker_is_refused_too() -> None:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    f4 = d.device("F4", "DEMO-MCB-3P")
    with pytest.raises(AuthorError, match=r"a fused branch is not a supply"):
        d.ac_supply("BRANCH", 230, x0[1], n=f4.element["2"])


def test_a_terminal_strip_still_declares_a_supply() -> None:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    ac = d.ac_supply("MAINS", 230, x0[1], n=x0[2])
    f4 = d.device("F4", "DEMO-MCB-2P")
    d.series(ac.L1, f4.pole_1, wire=(BK, 1.5))


def test_a_power_supplys_input_still_declares_a_supply() -> None:
    d = fr.design("demo_parts")
    psu = d.device("G1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
