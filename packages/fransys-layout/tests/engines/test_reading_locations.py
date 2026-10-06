"""U9 regression: `reading.location_infos` must not drop nested `+` aspect nodes."""

from fransys_layout.engines.schematic.read.reading import location_infos
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import Aspect, AspectNode

_ORIGIN = Origin(file="tests/engines/test_reading_locations.py", line=1, note="location_infos")

_EXPECTED_LOCATIONS = 2


def test_a_nested_location_node_is_included_alongside_the_root() -> None:
    """`+C1` at the root and `+C1+A1` nested under it both come back, not just the root."""
    root = AspectNode(
        id=make_id(AspectNode, ("c1",)),
        key=("c1",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="invented C1",
    )
    nested = AspectNode(
        id=make_id(AspectNode, ("c1", "a1")),
        key=("c1", "a1"),
        aspect=Aspect.LOCATION,
        parent=root.id,
        label="A1",
        description="invented A1",
    )
    draft = Draft()
    draft.extend((root, nested), origin=_ORIGIN)
    model = freeze(draft)

    locations = location_infos(model)

    assert len(locations) == _EXPECTED_LOCATIONS
    found = {info.location for info in locations}
    assert root.id in found
    assert nested.id in found
