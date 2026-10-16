"""Field case: one wire of a cable joins one terminal to one sensor pin, and a series takes one pin.

The engineering shape: a single core of a 3-core cable runs from one terminal of a strip
to one pin of a 2-wire sensor, and a lamp sits in a series between two terminals. A single
pin is a width-one end: it is one wire, not a group of wires.

The bug: `d.pair` refused a single pin at either end ("takes terminals or a function at
each end"), and its refusal text names neither the single pin nor a tuple of pins, so the
engineer could not tell which form to write. `d.series` with a single pin in the middle
is the same width-one case and must keep working.

Decision: author-0061 item 2 (a single pin or terminal is a width-one end of `d.pair`).
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys_author import AuthorError

from fransys_model.vocab.tables import conductors, functions, ports
lazy from fransys_model.vocab import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


def _cores(model: Model, cable: str) -> dict[str, frozenset[str]]:
    """Core number -> the two ends as `X8:1` or `B1:2`."""
    fns = functions(model)

    def end(port_id: Id[Port]) -> str:
        port = ports(model)[port_id]
        key = fns[port.function].key
        return f"{key[0]}:{key[2] if key[1] == 'terminal' else port.name}"

    return {
        c.key[-1]: frozenset({end(c.a), end(c.b)})
        for c in conductors(model).values()
        if c.key[0] == cable
    }


def test_pair_joins_one_terminal_to_one_pin() -> None:
    """Core 1 joins X8:1 to B1:1, the one wire of a width-one pair."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1], w3, b1.sig[1])
    assert _cores(fr.build(d).model, "W3") == {"1": frozenset({"X8:1", "B1:1"})}


def test_pair_refusal_names_a_pin_and_a_tuple_of_pins() -> None:
    """A non-port end is refused, and the message names both a single pin and a tuple of pins."""
    d = fr.design("demo_parts")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    with pytest.raises(AuthorError) as info:
        d.pair(5, w3, b1.sig)
    assert "a pin" in str(info.value)
    assert "a tuple of pins" in str(info.value)


def test_series_refusal_names_a_pin() -> None:
    """A series given a bare number is refused, and the message names a pin."""
    d = fr.design("demo_parts")
    h1 = d.device("H1", "DEMO-LAMP-24")
    with pytest.raises(AuthorError) as info:
        d.series(5, h1.lamp)
    assert "a pin" in str(info.value)


def test_series_takes_a_single_pin_at_each_end() -> None:
    """A lamp between X8:1 and X8:2 builds with no one-pin tuple and no wire override needed."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.series(x8[1], h1.lamp, x8[2], wire=1.0)
    fr.build(d)
