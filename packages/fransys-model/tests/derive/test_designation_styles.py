"""The other styles of the designation grammar: located ends and export names (EL-9 parts D, E)."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive.export_names import export_fragment
from fransys_model.derive.location_text import product_designation_in
from fransys_model.kernel import make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.enums import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Item


def _located_relay() -> tuple[Plant, Id[Item], Id[AspectNode], Id[AspectNode]]:
    """A relay `K1` placed at location `C1` then `SUB`: the plant, the relay, `C1`, `SUB`."""
    plant = Plant()
    relay = plant.item("relay", designation="K1")
    ids: dict[str, Id[AspectNode]] = {}
    for key, label, parent in (("c1", "C1", None), ("sub", "SUB", "c1")):
        node = AspectNode(
            id=make_id(AspectNode, (key,)),
            key=(key,),
            aspect=Aspect.LOCATION,
            parent=None if parent is None else ids[parent],
            label=label,
            description="Invented",
        )
        plant.add(node)
        ids[key] = node.id
    plant.add(Placement(id=make_id(Placement, ("pl",)), key=("pl",), item=relay, node=ids["sub"]))
    return plant, relay, ids["c1"], ids["sub"]


def test_a_located_item_drops_the_location_prefix_at_and_above_its_context() -> None:
    """Whole path with no context; below `C1` only `+SUB`; at `SUB` the prefix is gone."""
    plant, relay, cabinet, sub = _located_relay()
    model = plant.model()
    assert product_designation_in(model, relay, None, unit=None) == "+C1+SUB-K1"
    assert product_designation_in(model, relay, cabinet, unit=None) == "+SUB-K1"
    assert product_designation_in(model, relay, sub, unit=None) == "-K1"


def test_an_export_fragment_drops_the_leading_sign_and_dashes_the_others() -> None:
    """`=G1+C1-K1` gives `G1-C1-K1`; `-X2` gives `X2`."""
    assert export_fragment("=G1+C1-K1") == "G1-C1-K1"
    assert export_fragment("-X2") == "X2"
