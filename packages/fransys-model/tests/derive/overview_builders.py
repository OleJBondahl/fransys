"""An invented unit for the overview row tests: strip X1, devices K1 and K2, a nested unit."""

import dataclasses

from plant import Plant
from query_builders import make_pin, make_terminal

from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Item, Unit


def unit_plant() -> tuple[Model, Id[Unit], Id[Unit]]:
    """Unit `u` holds strip X1 (L1, L2), K1 and K2; nested `n` holds Z1; B1 is outside `u`.

    K1 has two wires to X1 (to L1 and to L2), K2 one, and two wires join K1 and K2; X1's L1
    external goes to B1; K1 to Z1; a jumper joins L1 to L2 inside the strip.
    """
    plant = Plant()
    outer = plant.unit("u", name="cab", tag="U1")
    nested = plant.unit("n", name="brd", parent=outer, tag="U2")
    plant.item("x1", designation="X1")
    t1 = make_terminal(plant, "x1", "t1", group="L", index=1)
    t2 = make_terminal(plant, "x1", "t2", group="L", index=2)
    k1, k2 = make_pin(plant, "k1", "K1"), make_pin(plant, "k2", "K2")
    k1b = plant.port(plant.function_id("k1", "f"), "2")
    z1, b1 = make_pin(plant, "z1", "Z1"), make_pin(plant, "b1", "B1")
    plant.wire(k1, t1.internal, key="w1")
    plant.wire(k1b, t2.internal, key="w2")
    plant.wire(k2, t2.internal, key="w3")
    plant.wire(t1.internal, t2.internal, key="jump")
    plant.wire(t1.external, b1, key="w4")
    plant.wire(k1, z1, key="w5")
    plant.wire(k1, k2, key="w6")
    plant.wire(k1b, k2, key="w7")
    plant.mate(plant.function_id("k1", "f"), plant.function_id("z1", "f"), key="m1")
    homes = {"x1": outer, "k1": outer, "k2": outer, "z1": nested}
    plant.records = [
        dataclasses.replace(r, unit=homes[r.key[0]])
        if isinstance(r, Item) and r.key[0] in homes
        else r
        for r in plant.records
    ]
    return plant.model(), outer, nested


def item_id(*key: str) -> Id[Item]:
    return make_id(Item, key)
