"""`location_node_designation` signs from the node: `+CAB` for a location, `=G` for a group."""

import fransys as fr

from fransys_layout.engines.schematic.read.reading import group_infos
from fransys_model.derive import location_node_designation
from fransys_model.vocab import Aspect, aspect_nodes


def test_the_sign_comes_from_the_nodes_own_aspect() -> None:
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        d.device("K1", "DEMO-RLY-2CO-24")
    model = fr.build(d).model
    text = {
        node.aspect: location_node_designation(model, node.id)
        for node in aspect_nodes(model).values()
        if node.label in {"CAB", "G"}
    }
    assert text == {Aspect.LOCATION: "+CAB", Aspect.FUNCTION: "=G"}


def test_the_layout_names_an_unnamed_group_by_that_designation() -> None:
    """V6a: `UNIT_GROUP_SPLIT` prints `GroupInfo.designation` for a group with no description."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    with d.function("G", ""):
        d.device("K1", "DEMO-RLY-2CO-24")
    (info,) = group_infos(fr.build(d).model)
    assert (info.description, info.designation) == ("", "=G")
