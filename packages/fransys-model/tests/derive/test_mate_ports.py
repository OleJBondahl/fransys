"""`mate_ports`: the one home of a mate's port pairs, equal port names paired once."""

from plant import Plant

from fransys_model.derive.facts.mates import mate_ports


def test_a_plug_and_a_socket_pair_their_pins_by_name_and_skip_the_unmatched_one() -> None:
    """Pins 1 and 2 meet by name; the plug's pin 3 has no namesake on the socket."""
    plant = Plant()
    plug = [plant.pin("plug", "J1", name) for name in ("1", "2", "3")]
    socket = [plant.pin("socket", "J1", name) for name in ("1", "2", "4")]
    plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    pairs = mate_ports(plant.model())
    assert pairs
    assert {frozenset(pair) for pair in pairs} == {
        frozenset((plug[0], socket[0])),
        frozenset((plug[1], socket[1])),
    }
    assert len(pairs) == 2
    assert pairs == tuple(sorted(pairs))
