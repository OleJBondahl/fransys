"""The overview lists a connector's pins in marking order: `A2` before `A10`.

Moved from the field case `test_a_connector_lists_a2_before_a10` (`overview_graph` is not on the
consumer surface). The overview once sorted a marking by number only when it was all digits.
Fixing decision: model-0153 (`marking_key` is the one marking order; amends model-0149).
"""

from fransys_model.derive import overview_graph

_PIN_ORDER = ["A2", "A10"]


def test_the_overview_lists_a2_first(plant):
    j1 = plant.item("j1", "J1", mpn="SIM-CONN-2P")
    j2 = plant.item("j2", "J2", mpn="SIM-CONN-2P")
    cable = plant.item("w1", "W1", mpn="SIM-CABLE")
    for core, pin in enumerate(reversed(_PIN_ORDER), start=1):
        plant.core(cable, (j1, pin), (j2, pin), f"core-{core}")
    signals = overview_graph(plant.freeze()).signals
    assert [signal.ports[0].marking for signal in signals] == _PIN_ORDER
