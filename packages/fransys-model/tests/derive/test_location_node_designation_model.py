"""`location_node_designation`: a location node's signed path, `location_designation`'s helper."""

from plant import Plant
from query_builders import make_node

from fransys_model.derive.designation import location_node_designation


def test_a_top_level_location_reads_its_own_signed_label() -> None:
    plant = Plant()
    c1 = make_node("c1", None)
    plant.add(c1)
    assert location_node_designation(plant.model(), c1.id) == "+C1"


def test_a_nested_location_reads_the_signed_path_root_to_leaf() -> None:
    plant = Plant()
    er = make_node("er", None)
    c1 = make_node("c1", er.id)
    sub = make_node("sub", c1.id)
    plant.add(er, c1, sub)
    model = plant.model()
    assert location_node_designation(model, c1.id) == "+ER+C1"
    assert location_node_designation(model, sub.id) == "+ER+C1+SUB"
