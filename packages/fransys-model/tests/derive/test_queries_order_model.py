"""WP16 tests: no query depends on the order of the tables."""

from typing import Any

from plant import Plant
from query_builders import (
    leg_net,
    make_board,
    make_core,
    make_labelled,
    make_part,
    make_pin,
    make_placement,
    make_plc,
    make_strip,
    make_tree,
    reversed_tables,
)

from fransys_model.derive import (
    board_netlist,
    bom_lines,
    cable_rows,
    conductors_on_item,
    designation_list,
    ext_usage,
    first_leg,
    items_at,
    plc_channel_rows,
    subtree,
    terminal_rows,
    unconnected_ports,
    unused_terminals,
    wire_rows,
)
from fransys_model.kernel import Model, make_id
from fransys_model.vocab.core import Item


def test_every_query_gives_the_same_answer_on_a_model_with_backwards_tables() -> None:
    """No result reads dict order: the whole set on a model built back to front."""
    plant = Plant()
    strip, _ = make_strip(plant)
    channels, _, _ = make_plc(plant)
    for number, key in enumerate(("ca", "cb")):  # two ends at one channel: `wired_to` is sorted
        plant.wire(
            plant.port(channels[0], "1"),
            make_pin(plant, f"chan-{key}", f"D{number}"),
            key=f"chan-{key}",
        )
    board = make_board(plant)
    cable = plant.item("w1", designation="W1")
    a, b = make_pin(plant, "ca", "B1"), make_pin(plant, "cb", "B2")
    make_core(plant, "core", cable, (a, b), index=1)
    make_labelled(plant, "lab", a, b, "L1")
    net, src, _ = leg_net(plant, wired_to=1)
    ids = make_tree(plant)
    plant.add(make_placement("p", make_id(Item, ("field-a",)), ids["left"]))
    plant.item("bom-1", part=make_part(plant, "relay", "R-1"), designation="K7")
    model = plant.model()

    def everything(m: Model) -> tuple[Any, ...]:
        return (
            conductors_on_item(m, strip),
            terminal_rows(m, strip),
            bom_lines(m),
            plc_channel_rows(m),
            cable_rows(m, cable),
            wire_rows(m),
            designation_list(m),
            first_leg(m, net, from_item=src),
            unconnected_ports(m),
            unused_terminals(m, strip),
            board_netlist(m, board),
            subtree(m, ids["root"]),
            items_at(m, ids["root"]),
            ext_usage(m),
        )

    assert everything(reversed_tables(model)) == everything(model)
