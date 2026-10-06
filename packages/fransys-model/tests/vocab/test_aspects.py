"""WP8 tests: aspect vocab kinds (ROADMAP WP8, design/vocabulary.md 6 "Structure")."""

from fransys_model.kernel import Id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.enums import Aspect


def test_aspect_node_has_the_designed_fields() -> None:
    """`AspectNode` carries `aspect`, `parent`, `label`, `description`."""
    node = AspectNode(
        id=Id(kind="aspect_node", value="1" * 32),
        key=("examples", "location", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="Invented example enclosure",
    )
    assert node.aspect is Aspect.LOCATION
    assert node.label == "C1"


def test_placement_has_the_designed_fields() -> None:
    """`Placement` carries `item`, `node`."""
    item_id = Id(kind="item", value="2" * 32)
    node_id = Id(kind="aspect_node", value="1" * 32)
    placement = Placement(
        id=Id(kind="placement", value="3" * 32),
        key=("examples", "relay-1", "at", "c1"),
        item=item_id,
        node=node_id,
    )
    assert placement.item == item_id
    assert placement.node == node_id
