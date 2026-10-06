"""Field case: a harness of one cable between two connectors whose pins are marked A2 and A10.

Engineering shape: a two-pin connector marks its pins with a letter and a number, `A2` and `A10`,
and a cable core lands on each pin at both ends.

The bug: the connector list, the harness and the overview listed `A10` before `A2` (a marking
sorted by number only when it was all digits), while the drawing listed `A2` first. The
pin order was four keys that disagreed.

Fixing decision: model-0153 (`marking_key` is the one marking order; amends model-0149).
"""

import fransys as fr
import pytest

_PIN_ORDER = ["A2", "A10"]


@pytest.fixture(scope="module")
def built() -> tuple[fr.BuildResult, object, object]:
    d = fr.design("demo_parts", place="C1")
    harness = d.harness("WH1", name="harness")
    j1 = d.device("J1", "DEMO-CONN-2P-LETTERED", parent=harness)
    j2 = d.device("J2", "DEMO-CONN-2P-LETTERED", parent=harness)
    cable = d.cable("W1", "DEMO-CBL-4G1.5", parent=harness, name="cable")
    for core, pin in enumerate(_PIN_ORDER, start=1):
        cable.core(core, j1.x1[pin], j2.x1[pin])
    return fr.build(d), j1, harness


def test_the_connector_rows_list_a2_first(built) -> None:
    result, j1, _ = built
    (row,) = fr.derive.connector_rows(result.model, j1.id)
    assert [pin.marking for pin in row.pins] == _PIN_ORDER


def test_the_harness_lists_a2_first(built) -> None:
    result, _, harness = built
    (cable,) = fr.derive.harness_cables(result.model, harness.id)
    assert [pin.marking for end in cable.ends for pin in end.pins] == _PIN_ORDER * 2


def test_the_overview_lists_a2_first(built) -> None:
    result, _, _ = built
    signals = fr.derive.overview_graph(result.model).signals
    assert [signal.ports[0].marking for signal in signals] == _PIN_ORDER


def test_the_pin_handles_the_drawing_is_authored_from_list_a2_first(built) -> None:
    _, j1, _ = built
    pins = [pin.name for pin in j1.x1.pins]
    assert pins == _PIN_ORDER
