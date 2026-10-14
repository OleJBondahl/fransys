"""An invented unit with two function groups for the folded-level tests (model-0199).

Unit `u` holds group =SUP (P1, D1, strips X1 and X2) and group =CTL (K1, K2, nested unit `n`
with Z1), and an ungrouped strip X9. Far unit `v` holds F1 and F2; B1 is in no unit.
"""

import dataclasses

from plant import Plant
from query_builders import make_pin, make_terminal

from fransys_model.kernel import Id, Model, make_id
from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import Aspect, ConductorKind

SUP = make_id(AspectNode, ("sup",))
CTL = make_id(AspectNode, ("ctl",))
SUP_BOX = OverviewRef(kind=OverviewRefKind.GROUP, node=SUP)
CTL_BOX = OverviewRef(kind=OverviewRefKind.GROUP, node=CTL)


def _group(plant: Plant, key: str, label: str, members: tuple[str, ...]) -> None:
    node = AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=Aspect.FUNCTION,
        parent=None,
        label=label,
        description=f"{label} group",
    )
    plant.add(node)
    for member in members:
        item = make_id(Item, (member,))
        plant.add(
            Placement(
                id=make_id(Placement, (key, member)), key=(key, member), item=item, node=node.id
            )
        )


def fold_plant(
    *, ctl_group: bool = True, external: tuple[str, ...] = ()
) -> tuple[Model, Id[Unit], Id[Unit]]:
    """The model, the unit `u` and the far unit `v`; `ctl_group` false leaves K1, K2, Z1 loose.

    The items keyed in `external` are by others.

    X1: t1 passes P1 to D1 through; t2 and t3 are bridged by a jumper, t2 fed by P1, t3 to D1.
    X2: t4 and t5 both pass P1 to D1 through. X9 (no group): t9 passes K2 to D1.
    Wires: P1-K1, K1-K2, K1-F1, K2-F2, K2-B1; a mate K1-Z1.
    """
    plant = Plant()
    outer = plant.unit("u", name="cab", tag="U1")
    nested = plant.unit("n", name="brd", parent=outer, tag="U2")
    far = plant.unit("v", name="far", tag="U9")
    for strip in ("x1", "x2", "x9"):
        plant.item(strip, designation=strip.upper())
    p1, d1 = make_pin(plant, "p1", "P1"), make_pin(plant, "d1", "D1")
    d1b = plant.port(plant.function_id("d1", "f"), "2")
    k1, k2 = make_pin(plant, "k1", "K1"), make_pin(plant, "k2", "K2")
    make_pin(plant, "z1", "Z1")
    b1 = make_pin(plant, "b1", "B1")
    f1, f2 = make_pin(plant, "f1", "F1"), make_pin(plant, "f2", "F2")
    t1, t2, t3 = (make_terminal(plant, "x1", f"t{n}", group="L", index=n) for n in (1, 2, 3))
    t4, t5 = (make_terminal(plant, "x2", f"t{n}", group="L", index=n) for n in (4, 5))
    t9 = make_terminal(plant, "x9", "t9", group="L", index=9)
    for key, a, b in (
        ("w1", p1, t1.internal),
        ("w2", t1.external, d1),
        ("w3", p1, t2.internal),
        ("w4", t3.external, d1b),
        ("w5", p1, t4.internal),
        ("w6", t4.external, d1),
        ("w7", p1, t5.internal),
        ("w8", t5.external, d1b),
        ("w9", k2, t9.internal),
        ("w10", t9.external, d1),
        ("w11", p1, k1),
        ("w12", k1, k2),
        ("w13", k1, f1),
        ("w14", k2, f2),
        ("w15", k2, b1),
    ):
        plant.wire(a, b, key=key)
    plant.wire(t2.internal, t3.internal, key="jump", kind=ConductorKind.JUMPER)
    plant.mate(plant.function_id("k1", "f"), plant.function_id("z1", "f"), key="m1")
    _group(plant, "sup", "SUP", ("p1", "d1", "x1", "x2"))
    if ctl_group:
        _group(plant, "ctl", "CTL", ("k1", "k2", "z1"))
    homes = {"x1": outer, "x2": outer, "x9": outer, "p1": outer, "d1": outer, "k1": outer}
    homes |= {"k2": outer, "z1": nested, "f1": far, "f2": far}
    plant.records = [
        dataclasses.replace(r, unit=homes.get(r.key[0]), external=r.key[0] in external)
        if isinstance(r, Item)
        else r
        for r in plant.records
    ]
    return plant.model(), outer, far
