"""Field case: a pair through a cable takes a tuple of pins, or a part of a function, at either end.

The engineering shape: a 2-wire sensor B1 is wired to two terminals X8:1 and X8:2 of a strip
through the 2-core cable W3. The engineer names the two sensor pins as a tuple, or takes the
first two pins of the sensor's signal function, and joins them pin for pin.

The bug: `d.pair` accepted terminal ranges (`x8[1:3]`) and whole functions (`b1.sig`) but
refused a tuple of ports at either end and a slice of a function's pins. The refusal reads
"takes terminals or a function at each end", so the engineer cannot write the two-pin group
they mean. A tuple of pins from two devices is refused by the series grammar, and `d.pair`
must refuse it with the same message.

Decision: author-0061 item 3 (`d.pair` takes a tuple of pins and a part of a function).
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


def test_pair_takes_a_tuple_of_pins_at_the_second_end() -> None:
    """Core 1 joins X8:1 to B1:1 and core 2 joins X8:2 to B1:2, the sensor end as a tuple."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, (b1.sig[1], b1.sig[2]))
    assert _cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_takes_a_part_of_a_function() -> None:
    """A slice of the sensor's signal function, its first two pins, joins pin for pin."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, b1.sig.pins[:2])
    assert _cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_takes_a_tuple_of_pins_at_the_first_end() -> None:
    """A tuple at the first end joins B1:1 to X8:1 and B1:2 to X8:2."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair((b1.sig[1], b1.sig[2]), w3, x8[1:3])
    assert _cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_refuses_a_tuple_of_pins_from_two_devices() -> None:
    """A tuple whose pins belong to two devices is refused, as a series refuses it."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    b2 = d.device("B2", "DEMO-SENSOR-2W")
    with pytest.raises(AuthorError, match="holds the pins of one device"):
        d.pair(x8[1:3], w3, (b1.sig[1], b2.sig[2]))
