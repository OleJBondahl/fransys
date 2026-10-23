"""The designation grammar (EL-9, model-0331): segments, one renderer, a context, the scheme."""

from typing import TYPE_CHECKING

import pytest
from plant import Plant

from fransys_model.derive.designation import location_node_designation
from fransys_model.derive.rows_designation import Segment
from fransys_model.derive.texts.context import PrintContext
from fransys_model.derive.texts.designation_render import aspect_text, designation_text, node_text
from fransys_model.derive.texts.designation_segments import designation_segments, node_segments
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab import DESIGNATION_SCHEME
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Unit
from fransys_model.vocab.enums import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Id


def _node(plant: Plant, key: str, aspect: Aspect, label: str, parent: Id[AspectNode] | None):
    node = AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=parent,
        label=label,
        description="Invented",
    )
    plant.add(node)
    return node.id


def _place(plant: Plant, item: Id, node: Id[AspectNode]) -> None:
    key = f"place-{node.value}"
    plant.add(Placement(id=make_id(Placement, (key,)), key=(key,), item=item, node=node))


def _located_relay() -> tuple[Plant, Id, Id, Id, Id]:
    """A relay `K1` on board `A1`, placed at function `G1` and location `C1` then `SUB`."""
    plant = Plant()
    board = plant.item("board", part=plant.board_part(), designation="A1")
    relay = plant.item("relay", designation="K1", parent=board)
    group = _node(plant, "g1", Aspect.FUNCTION, "G1", None)
    cabinet = _node(plant, "c1", Aspect.LOCATION, "C1", None)
    sub = _node(plant, "sub", Aspect.LOCATION, "SUB", cabinet)
    for node in (group, sub):
        _place(plant, relay, node)
    return plant, board, relay, cabinet, sub


def test_a_designation_is_a_chain_of_dash_segments_and_the_context_drops_a_board() -> None:
    """The board's segment is in front; a context naming the board drops it and all above."""
    plant, board, relay, _, _ = _located_relay()
    model = plant.model()
    whole = designation_segments(model, relay, PrintContext())
    assert whole == (Segment(sign="-", label="A1"), Segment(sign="-", label="K1"))
    cut = designation_segments(model, relay, PrintContext(board=board))
    assert cut == (Segment(sign="-", label="K1"),)
    assert designation_text(model, relay, PrintContext()) == "A1-K1"
    assert designation_text(model, relay, PrintContext(), bare=False) == "-A1-K1"


def test_a_location_prefix_drops_at_and_above_the_context_location() -> None:
    """`+C1+SUB` whole; below `C1` only `+SUB`; at `SUB` nothing is left."""
    plant, _, _, cabinet, sub = _located_relay()
    model = plant.model()
    assert node_text(model, sub, PrintContext()) == "+C1+SUB"
    assert node_text(model, sub, PrintContext(location=cabinet)) == "+SUB"
    assert node_text(model, sub, PrintContext(location=sub)) == ""
    assert node_segments(model, None, PrintContext()) == ()


def test_a_reference_prints_the_function_segment_before_the_location_segment() -> None:
    """The scheme's `reference_aspects` order, not the order the placements were added."""
    plant, _, relay, _, _ = _located_relay()
    assert aspect_text(plant.model(), relay, PrintContext()) == "=G1+C1+SUB"


def test_the_scheme_holds_a_sign_per_aspect_and_the_iec_letter_rules() -> None:
    """Every aspect has its sign; A, I, O are forbidden and D, L, V, Y, Z reserved."""
    scheme = DESIGNATION_SCHEME
    assert {aspect: scheme.sign(aspect) for aspect in Aspect} == {
        Aspect.FUNCTION: "=",
        Aspect.PRODUCT: "-",
        Aspect.LOCATION: "+",
    }
    assert scheme.reference_aspects == (Aspect.FUNCTION, Aspect.LOCATION)
    assert scheme.forbidden_letters == frozenset("AIO")
    assert scheme.reserved_letters == frozenset("DLVYZ")
    assert [scheme.letter_rule(code) for code in ("A1", "O", "K", "Z", "DX")] == [
        "forbidden",
        "forbidden",
        None,
        "reserved",
        "reserved",
    ]
    assert scheme.class_code == "[A-Z]{1,3}"


def test_the_scheme_join_writes_each_sign_and_leaves_the_first_off_when_bare() -> None:
    """The one join: `-U1-U3`, bare `U1-U3`; an empty chain is empty."""
    pairs = (("-", "U1"), ("-", "U3"))
    assert DESIGNATION_SCHEME.join(pairs) == "-U1-U3"
    assert DESIGNATION_SCHEME.join(pairs, bare=True) == "U1-U3"
    assert DESIGNATION_SCHEME.join((), bare=True) == ""
    assert DESIGNATION_SCHEME.signed(Aspect.PRODUCT, "K1") == "-K1"


def test_a_context_naming_a_unit_the_model_lacks_is_refused_naming_the_context() -> None:
    """No silent whole form: a text built in the reading of an absent unit raises."""
    plant, _, relay, _, sub = _located_relay()
    model = plant.model()
    ghost = PrintContext(reading=make_id(Unit, ("ghost",)))
    for build in (
        lambda: designation_segments(model, relay, ghost),
        lambda: node_segments(model, sub, ghost),
        lambda: designation_text(model, relay, ghost),
        lambda: node_text(model, sub, ghost),
    ):
        with pytest.raises(SchemaError, match=r"PrintContext\.reading .* not a unit of the model"):
            build()
    assert designation_text(model, relay, PrintContext(reading=None)) == "A1-K1"


def test_a_product_node_prints_its_dash_designation() -> None:
    """Ruling 32: a product node prints `-JB1` (it was a KeyError)."""
    plant = Plant()
    product = _node(plant, "jb1-product", Aspect.PRODUCT, "JB1", None)
    assert location_node_designation(plant.model(), product) == "-JB1"
