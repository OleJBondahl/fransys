"""Units spec U7: the stage's marker box and the model reader's `marker_text` must agree on a
severed cut with no common ancestor at all (`+ER+C1` to `+AR+C1`) -- the one shape the narrow
golden (`test_drawing_text_equality.py`) never reaches, by its own docstring, since it stays
in one location throughout. `_reading.location_path` (the stage side) and
`drawing_text.location_path` (the reader side) are two independent walks of one
`AspectNode.parent` chain; this proves they still agree, not just that the shared
`location_prefix`/`position_text` formatters do.

A declared `Net` (not a `Connection`) between two locations with no common ancestor gives each
end a stub label (D4, LD7: "a wire that leaves its drawing ends in a stub label... both of its
ends always carry one number"), not a `#` reference. The stub's box is sized to its own text
(its `+<label>` location prefix included, LD5 units spec U7): the box's length along the text
(`height` for a vertical N/S box, S20 M1/M2, else `width`) holds the printed text.
"""

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import LinkMarker, Page, StarKind, layout_of
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Placement,
    Port,
    PortRole,
)

_ORIGIN = Origin(file="tests/test_marker_text_agrees_across_nested_locations.py", line=1, note="U7")
_EXPECTED_MARKER_COUNT = 2


def _location(key: tuple[str, ...], label: str, *, parent: AspectNode | None) -> AspectNode:
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=Aspect.LOCATION,
        parent=None if parent is None else parent.id,
        label=label,
        description=f"invented {label}",
    )


def _item_at(tag: str) -> tuple[Item, Function, Port]:
    item = Item(
        id=make_id(Item, ("probe", tag)),
        key=("probe", tag),
        part=None,
        parent=None,
        position=None,
        tag=tag,
        description=f"invented {tag}",
    )
    function = Function(
        id=make_id(Function, (*item.key, "fn")),
        key=(*item.key, "fn"),
        item=item.id,
        template=None,
        name="fn",
        kind=FunctionKind.CONNECTOR,
    )
    port = Port(
        id=make_id(Port, (*function.key, "1")),
        key=(*function.key, "1"),
        function=function.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return item, function, port


def _placements(item: Item, group: AspectNode, location: AspectNode) -> tuple[Placement, ...]:
    def _one(node: AspectNode) -> Placement:
        key = (*item.key, "at", *node.key)
        return Placement(id=make_id(Placement, key), key=key, item=item.id, node=node.id)

    return tuple(_one(node) for node in (group, location))


def test_marker_text_fits_its_box_across_two_unrelated_locations() -> None:
    """`+ER+C1` to `+AR+C1`: net `S`, page `p1` in EACH drawing set (the `ER`/`AR` sets), the
    two probe ports `p1_port`/`p2_port` -- named precisely, per the designer's own request.

    Confirms each end is a stub label (D4, `star is StarKind.OFF`, `far` set to the other
    port), never a `#` reference (LD7: a wire that leaves its drawing ends in a stub label,
    not a reference), and that the stub's box -- sized to its own text, not LD3's fixed
    reference box -- fits the real printed text (with its `+<label>` prefix, U7). Measured,
    not assumed.
    """
    er = _location(("probe", "er"), "ER", parent=None)
    er_c1 = _location(("probe", "er", "c1"), "C1", parent=er)
    ar = _location(("probe", "ar"), "AR", parent=None)
    ar_c1 = _location(("probe", "ar", "c1"), "C1", parent=ar)
    grp = AspectNode(
        id=make_id(AspectNode, ("probe", "grp")),
        key=("probe", "grp"),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="G",
        description="invented group",
    )
    p1_item, p1_fn, p1_port = _item_at("p1")
    p2_item, p2_fn, p2_port = _item_at("p2")
    # C21 (deep dive): a conductor between two locations is drawn as stubs, not markers; a
    # declared net between them is still a marker pair, so the fixture's cut is a net
    net = Net(
        id=make_id(Net, ("probe", "net")),
        key=("probe", "net"),
        name="S",
        net_class=NetClass.CONTROL,
        ports=(p1_port.id, p2_port.id),
    )
    draft = Draft()
    draft.extend(
        (
            er,
            er_c1,
            ar,
            ar_c1,
            grp,
            p1_item,
            p2_item,
            p1_fn,
            p2_fn,
            p1_port,
            p2_port,
            *_placements(p1_item, grp, er_c1),
            *_placements(p2_item, grp, ar_c1),
            net,
        ),
        origin=_ORIGIN,
    )
    written, _findings = lay_out_schematic(freeze(draft))

    markers = layout_of(written, LinkMarker)
    assert len(markers) == _EXPECTED_MARKER_COUNT
    pages = layout_of(written, Page)
    # Named for the designer, precisely: net "S" (net.name above), page "p1" in each of the
    # two drawing sets (ER's and AR's), the two probe ports p1_port/p2_port (below).
    assert {pages[m.page].number for m in markers.values()} == {1}
    assert {m.port for m in markers.values()} == {p1_port.id, p2_port.id}

    # D4/LD7: no common ancestor means a stub label at each end, never a `#` reference.
    for marker in markers.values():
        assert marker.star is StarKind.OFF
        assert marker.far in {p1_port.id, p2_port.id}
        text = marker_text(written, marker)
        assert text in {"← +AR+C1-p2:1", "← +ER+C1-p1:1"}
        assert "#" not in text
        needed = text_width(text, height=DEFAULT_PROFILE.text_height) + (
            2 * DEFAULT_PROFILE.marker_padding
        )
        along = marker.height if marker.vertical else marker.width  # the box's length (M2)
        assert needed <= along, f"{text!r} needs {needed} G, the stub box is only {along} G"
