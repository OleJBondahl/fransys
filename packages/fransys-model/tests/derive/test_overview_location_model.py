"""`location_fold` (model-0199, O9) is absent under two top places; tests/test_overview_levels.py
holds the folded boxes on the units example, where cables give the system level its boxes."""

from cable_drawing_builders import cable, device, edit
from plant import Plant

from fransys_model.derive import location_fold, location_place_title
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet


def _model(places: int) -> Model:
    """Items A1, A2 and B1; `places` location nodes +P0, +P1 hold A1 and A2, then B1."""
    plant = Plant()
    for key in ("a1", "a2", "b1", "c1"):
        plant.item(key, designation=key.upper())
    nodes = []
    for at in range(places):
        node = AspectNode(
            id=make_id(AspectNode, (f"p{at}",)),
            key=(f"p{at}",),
            aspect=Aspect.LOCATION,
            parent=None,
            label=f"P{at}",
            description="Place",
        )
        nodes.append(node)
        plant.add(node)
    for key, node in (("a1", 0), ("a2", 0), ("b1", 1)):
        if node < places:
            plant.add(
                Placement(
                    id=make_id(Placement, (key,)),
                    key=(key,),
                    item=make_id(Item, (key,)),
                    node=nodes[node].id,
                )
            )
    return plant.model()


def test_the_fold_is_absent_under_two_top_places() -> None:
    """No place and one place give no fold; the switch is absent (O9)."""
    assert location_fold(_model(0)) is None
    assert location_fold(_model(1)) is None


def _cabled_plant(*, across: bool) -> tuple[Model, dict[str, Id[Item]]]:
    """Units UA and UB in +P0, UC in +P1; cable W1 joins UA and UB, W2 (if `across`) UA and UC."""
    plant = Plant()
    units = {key: plant.unit(key, name=key, tag=key.upper()) for key in ("ua", "ub", "uc")}
    ports = {}
    for key, tag in (("a1", "ua"), ("a2", "ub"), ("b1", "uc")):
        _, found = device(plant, key, key.upper(), "1", unit=units[tag])
        ports[key] = found["1"]
    cables = {key: cable(plant, key, key.upper()) for key in ("w1", "w2")}
    for key in cables:
        edit(plant, make_id(CableProductFacet, (key, "part", "product")), core_colours=("BN",))
    runs = [("c1", "a1", "a2", "w1")] + ([("c2", "a1", "b1", "w2")] if across else [])
    for key, near, far, cable_key in runs:
        core = plant.core(ports[near], ports[far], key=key, carrier=cables[cable_key])
        plant.add(
            CoreFacet(
                id=make_id(CoreFacet, (key, "facet")), key=(key, "facet"), subject=core, index=1
            )
        )
    nodes = {}
    for at in (0, 1):
        node = AspectNode(
            id=make_id(AspectNode, (f"p{at}",)),
            key=(f"p{at}",),
            aspect=Aspect.LOCATION,
            parent=None,
            label=f"P{at}",
            description="Place",
        )
        nodes[at] = node
        plant.add(node)
    for key, at in (("a1", 0), ("a2", 0), ("b1", 1)):
        item = make_id(Item, (key,))
        plant.add(
            Placement(id=make_id(Placement, (key,)), key=(key,), item=item, node=nodes[at].id)
        )
    return plant.model(), cables


def test_a_cable_inside_one_place_gives_no_location_line() -> None:
    """W1 joins two devices of +P0, so it is no line; with W2 across the places, only W2 is one."""
    model, cables = _cabled_plant(across=False)
    alone = location_fold(model)
    assert alone is not None
    assert alone.lines == ()
    model, cables = _cabled_plant(across=True)
    fold = location_fold(model)
    assert fold is not None
    assert [(line.count, line.cables) for line in fold.lines] == [(1, (cables["w2"],))]


def test_a_place_title_is_its_designation_then_its_text() -> None:
    """The panel title and the box lines share one function (overview-0007)."""
    node = make_id(AspectNode, ("p0",))
    assert location_place_title(_model(2), node) == "+P0 Place"
