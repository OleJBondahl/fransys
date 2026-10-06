"""WP14 tests: `derive.designation` (ROADMAP WP14, design/derive-text.md and
design/examples.md 11)."""

from derive_helpers import add_all

from fransys_model.derive import reference_designation
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect


def test_reference_designation_renders_function_location_product(origin: Origin) -> None:
    """A `Placement` in the function and location aspects renders `=A1+C1-K1`.

    The trailing product segment is always the item's own `item_designation`, never a
    separate product-aspect `Placement` label, so there is no double dash (design/derive-text.md).
    """
    draft = Draft()
    item = Item(
        id=Id(kind="item", value="1" * 32),
        key=("k1",),
        part=None,
        parent=None,
        position=None,
        tag="K1",
        description="pump starter",
    )
    function_node = AspectNode(
        id=Id(kind="aspect_node", value="1" * 32),
        key=("fn", "a1"),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="A1",
        description="pump control function",
    )
    location_node = AspectNode(
        id=Id(kind="aspect_node", value="2" * 32),
        key=("loc", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="pump enclosure",
    )
    placement_function = Placement(
        id=Id(kind="placement", value="1" * 32),
        key=("k1", "fn"),
        item=item.id,
        node=function_node.id,
    )
    placement_location = Placement(
        id=Id(kind="placement", value="2" * 32),
        key=("k1", "loc"),
        item=item.id,
        node=location_node.id,
    )
    add_all(
        draft,
        item,
        function_node,
        location_node,
        placement_function,
        placement_location,
        origin=origin,
    )
    model = freeze(draft)
    assert reference_designation(model, item.id) == "=A1+C1-K1"
