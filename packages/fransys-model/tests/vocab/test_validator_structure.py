"""WP13 tests: `validators.structure` (ROADMAP WP13, design/vocabulary.md 6)."""

from scaffold import scaffold

from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.validators.structure import (
    ASPECT_CROSS_PARENT,
    ASPECT_CYCLE,
    CONTAINMENT_CYCLE,
    PLACEMENT_DUPLICATE,
    check_structure,
)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_structure.py", line=1, note="fixture")
    draft.extend((*records, *scaffold(records)), origin=origin)
    return freeze(draft)


def _bare_node(node_id: Id[AspectNode], aspect: Aspect, name: str) -> AspectNode:
    """Setup only: a node a placement refers to, of the aspect the test needs."""
    return AspectNode(
        id=node_id,
        key=("examples", aspect.value, name),
        aspect=aspect,
        parent=None,
        label="N",
        description="",
    )


def test_aspect_tree_without_a_cycle_has_no_finding() -> None:
    """A `+C1` node with no parent is an acyclic, single-node tree."""
    node = AspectNode(
        id=Id(kind="aspect_node", value="1" * 32),
        key=("examples", "location", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="",
    )
    findings = check_structure(_freeze((node,)))
    assert not [f for f in findings if f.code == ASPECT_CYCLE]


def test_aspect_node_parent_cycle_yields_aspect_cycle() -> None:
    """Node A's parent is node B and node B's parent is node A: `ASPECT_CYCLE`."""
    a_id = Id(kind="aspect_node", value="2" * 32)
    b_id = Id(kind="aspect_node", value="3" * 32)
    node_a = AspectNode(
        id=a_id,
        key=("examples", "location", "a"),
        aspect=Aspect.LOCATION,
        parent=b_id,
        label="A",
        description="",
    )
    node_b = AspectNode(
        id=b_id,
        key=("examples", "location", "b"),
        aspect=Aspect.LOCATION,
        parent=a_id,
        label="B",
        description="",
    )
    findings = check_structure(_freeze((node_a, node_b)))
    assert any(f.code == ASPECT_CYCLE for f in findings)


def test_node_parented_within_its_own_aspect_has_no_finding() -> None:
    """A `LOCATION` node parented under another `LOCATION` node is fine."""
    parent_id = Id(kind="aspect_node", value="4" * 32)
    parent = AspectNode(
        id=parent_id,
        key=("examples", "location", "site"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="Site",
        description="",
    )
    child = AspectNode(
        id=Id(kind="aspect_node", value="5" * 32),
        key=("examples", "location", "c1"),
        aspect=Aspect.LOCATION,
        parent=parent_id,
        label="C1",
        description="",
    )
    findings = check_structure(_freeze((parent, child)))
    assert not [f for f in findings if f.code == ASPECT_CROSS_PARENT]


def test_node_parented_across_aspects_yields_aspect_cross_parent() -> None:
    """A `PRODUCT` node parented under a `LOCATION` node yields `ASPECT_CROSS_PARENT`."""
    parent_id = Id(kind="aspect_node", value="6" * 32)
    parent = AspectNode(
        id=parent_id,
        key=("examples", "location", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="",
    )
    child = AspectNode(
        id=Id(kind="aspect_node", value="7" * 32),
        key=("examples", "product", "k1"),
        aspect=Aspect.PRODUCT,
        parent=parent_id,
        label="K1",
        description="",
    )
    findings = check_structure(_freeze((parent, child)))
    assert any(f.code == ASPECT_CROSS_PARENT for f in findings)


def test_one_placement_per_item_per_aspect_has_no_finding() -> None:
    """One `PRODUCT` placement and one `LOCATION` placement for the same item is fine."""
    item_id = Id(kind="item", value="8" * 32)
    node_product = Id(kind="aspect_node", value="9" * 32)
    node_location = Id(kind="aspect_node", value="a" * 32)
    placements = (
        Placement(
            id=Id(kind="placement", value="b" * 32),
            key=("examples", "relay-1", "at-product"),
            item=item_id,
            node=node_product,
        ),
        Placement(
            id=Id(kind="placement", value="c" * 32),
            key=("examples", "relay-1", "at-location"),
            item=item_id,
            node=node_location,
        ),
    )
    nodes = (
        _bare_node(node_product, Aspect.PRODUCT, "product"),
        _bare_node(node_location, Aspect.LOCATION, "location"),
    )
    findings = check_structure(_freeze((*placements, *nodes)))
    assert not [f for f in findings if f.code == PLACEMENT_DUPLICATE]


def test_two_placements_in_the_same_aspect_yields_placement_duplicate() -> None:
    """Two `LOCATION` placements for the same item yields `PLACEMENT_DUPLICATE`."""
    item_id = Id(kind="item", value="d" * 32)
    placements = (
        Placement(
            id=Id(kind="placement", value="e" * 32),
            key=("examples", "relay-1", "at-c1"),
            item=item_id,
            node=Id(kind="aspect_node", value="f" * 32),
        ),
        Placement(
            id=Id(kind="placement", value="1" * 32),
            key=("examples", "relay-1", "at-c2"),
            item=item_id,
            node=Id(kind="aspect_node", value="2" * 32),
        ),
    )
    nodes = tuple(
        _bare_node(placement.node, Aspect.LOCATION, f"location-{number}")
        for number, placement in enumerate(placements)
    )
    findings = check_structure(_freeze((*placements, *nodes)))
    assert any(f.code == PLACEMENT_DUPLICATE for f in findings)


def test_item_parent_chain_without_a_cycle_has_no_finding() -> None:
    """A terminal `Item` parented under a strip `Item` is fine."""
    strip_id = Id(kind="item", value="3" * 32)
    strip = Item(
        id=strip_id,
        key=("examples", "x03"),
        part=None,
        parent=None,
        position=None,
        tag="X03",
        description="",
    )
    terminal = Item(
        id=Id(kind="item", value="4" * 32),
        key=("examples", "x03", "l1-1"),
        part=None,
        parent=strip_id,
        position=None,
        tag=None,
        description="",
    )
    findings = check_structure(_freeze((strip, terminal)))
    assert not [f for f in findings if f.code == CONTAINMENT_CYCLE]


def test_item_parent_cycle_yields_containment_cycle() -> None:
    """Item A's parent is item B and item B's parent is item A: `CONTAINMENT_CYCLE`."""
    a_id = Id(kind="item", value="5" * 32)
    b_id = Id(kind="item", value="6" * 32)
    item_a = Item(
        id=a_id,
        key=("examples", "a"),
        part=None,
        parent=b_id,
        position=None,
        tag=None,
        description="",
    )
    item_b = Item(
        id=b_id,
        key=("examples", "b"),
        part=None,
        parent=a_id,
        position=None,
        tag=None,
        description="",
    )
    findings = check_structure(_freeze((item_a, item_b)))
    assert any(f.code == CONTAINMENT_CYCLE for f in findings)
