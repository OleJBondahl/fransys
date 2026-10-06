"""`unit_cables` reads unit-relative and `unit_cable_page_key` (decision model-0090).

The owner's rule: "a unit's drawing shows nothing above the unit". A nested unit's cable prints
its ends against the unit's own location and its outside end as `""` (model-0056), a top-level
unit's outside end by path; the absolute cable queries never move. Invented data, one model:
two harnesses at `+C1` (`WH1` in the nested unit `hu`, `WH2` in the top-level unit `top`), a
relay board `A1` at `+C1` (the root of the nested unit `bu`, holding `K1` and a strip `S1`), and
one device `M1` at `+EXT` in no unit that every cable runs to. A harness root's tag is not
dropped by `item_designation(unit=)` (only a board root's is, `_unit_root`), so the tag-dropping
checks use the board unit.
"""

import dataclasses
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from query_builders import make_core, make_node, make_placement, make_terminal

from fransys_model.derive import (
    cable_rows,
    harness_cables,
    top_level_cables,
    unit_cable_page_key,
    unit_cables,
)
from fransys_model.derive.designation import product_designation
from fransys_model.derive.drawing_text import product_designation_in
from fransys_model.derive.harness import all_cables
from fransys_model.kernel import SchemaError, make_id
from fransys_model.kernel.ids import render_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from fransys_model.derive.rows import HarnessCable
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.core import Item, Port


@dataclass(frozen=True)
class _Design:
    model: Model
    hu: Id[Unit]
    top: Id[Unit]
    bu: Id[Unit]
    wh1: Id[Item]
    w1: Id[Item]
    plug: Id[Item]
    w2: Id[Item]
    w3: Id[Item]
    k1: Id[Item]
    strip: Id[Item]
    harness_strip: Id[Item]
    m1: Id[Item]
    c1: Id[AspectNode]


def _in_unit(plant: Plant, item: Id[Item], unit: Id[Unit]) -> None:
    """Replace the plant's record for `item` by a copy in `unit` (`make_terminal` sets none)."""
    (at,) = [n for n, record in enumerate(plant.records) if record.id == item]
    plant.records[at] = dataclasses.replace(plant.records[at], unit=unit)


def _cable(
    plant: Plant, key: str, tag: str, unit: Id[Unit], parent: Id[Item] | None = None
) -> Id[Item]:
    """A cable `tag` in `unit`, in `parent` when given: a cable `Part` (`is_cable`, decision
    model-0108) and a `cable` facet."""
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, (key, "part", "product")),
        key=(key, "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(part, product)
    item = plant.item(key, designation=tag, parent=parent, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )
    return item


def _ports(plant: Plant, item: Id[Item], *names: str) -> list[Id[Port]]:
    """One function of `item` with one port per name."""
    function = plant.function(item, "f")
    return [plant.port(function, name) for name in names]


def _design() -> _Design:
    """The model described above.

    `W1` (in `WH1`) runs plug `X1` to `M1:1` and strip `X2` (terminal `L:1`) to `M1:2`; `W2` (in
    `WH2`) runs plug `X3` to `M1:3`; `W3` (in the board `A1`) runs `K1` to `M1:4` and strip `S1`
    (terminal `L:2`, of the board) to `M1:5`.
    """
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    cabinet = plant.unit("cabinet", name="cabinet")
    hu = plant.unit("hu", name="hu", parent=cabinet)
    bu = plant.unit("bu", name="bu", parent=cabinet)
    top = plant.unit("top", name="top")
    m1 = plant.item("m1", designation="M1")
    plant.add(make_placement("m1-loc", m1, ext.id))
    m1_ports = _ports(plant, m1, "1", "2", "3", "4", "5")
    placed = []

    wh1 = plant.item("wh1", designation="WH1", unit=hu)
    plug = plant.item("x1", designation="X1", parent=wh1, unit=hu)
    harness_strip = plant.item("x2", designation="X2", parent=wh1, unit=hu)
    terminal = make_terminal(plant, "x2", "t", group="L", index=1)
    _in_unit(plant, terminal.item, hu)
    w1 = _cable(plant, "w1", "W1", hu, wh1)
    (plug_pin,) = _ports(plant, plug, "1")
    make_core(plant, "c-plug", w1, (plug_pin, m1_ports[0]), index=1)
    make_core(plant, "c-strip", w1, (terminal.external, m1_ports[1]), index=2)
    placed += [wh1, plug, harness_strip]

    wh2 = plant.item("wh2", designation="WH2", unit=top)
    far = plant.item("x3", designation="X3", parent=wh2, unit=top)
    w2 = _cable(plant, "w2", "W2", top, wh2)
    (far_pin,) = _ports(plant, far, "1")
    make_core(plant, "c-far", w2, (far_pin, m1_ports[2]), index=1)
    placed += [wh2, far]

    board = plant.item("a1", designation="A1", part=plant.board_part(), unit=bu)
    k1 = plant.item("k1", designation="K1", parent=board, unit=bu)
    board_strip = plant.item("s1", designation="S1", parent=board, unit=bu)
    board_terminal = make_terminal(plant, "s1", "t", group="L", index=2)
    _in_unit(plant, board_terminal.item, bu)
    w3 = _cable(plant, "w3", "W3", bu, board)
    (k1_pin,) = _ports(plant, k1, "1")
    make_core(plant, "c-k1", w3, (k1_pin, m1_ports[3]), index=1)
    make_core(plant, "c-s1", w3, (board_terminal.external, m1_ports[4]), index=2)
    placed += [board, k1, board_strip]

    for number, item in enumerate(placed):
        plant.add(make_placement(f"placed-{number}", item, c1.id))
    return _Design(
        plant.model(), hu, top, bu, wh1, w1, plug, w2, w3, k1, board_strip, harness_strip, m1, c1.id
    )


def _by_cable(design: _Design) -> dict[Id[Item], HarnessCable]:
    """`all_cables`, the absolute query that reads every cable of the model, by cable id."""
    return {cable.cable: cable for cable in all_cables(design.model)}


# -- the unit view ------------------------------------------------------------------------------


def test_a_nested_units_cable_prints_its_outside_end_as_empty() -> None:
    """`hu` is nested: `M1` at `+EXT`, in no unit, reads `""`; the harness root's tag stays."""
    design = _design()
    (cable,) = unit_cables(design.model, design.hu)
    assert cable.cable == design.w1
    assert cable.designation == "-WH1-W1"
    assert [end.designation for end in cable.ends] == ["-WH1-X1", "-WH1-X2", ""]
    assert [(core.end_a_designation, core.end_b_designation) for core in cable.cores] == [
        ("-WH1-X1:1", ""),
        ("-WH1-X2:L:1", ""),
    ]


def test_a_nested_units_cable_reads_unit_relative() -> None:
    """A board unit's cable, ends and cores drop the board's tag and location: `-K1`, `-S1`."""
    design = _design()
    (cable,) = unit_cables(design.model, design.bu)
    assert cable.cable == design.w3
    assert cable.designation == "-W3"
    assert [end.designation for end in cable.ends] == ["-K1", "-S1", ""]
    assert [(core.end_a_designation, core.end_b_designation) for core in cable.cores] == [
        ("-K1:1", ""),
        ("-S1:L:2", ""),
    ]


def test_a_terminal_strip_pin_marking_is_bare_in_every_reading() -> None:
    """A strip's terminal pin is the bare `group:index` (model-0052), in a unit's and the absolute.

    The board strip's `L:2` and the harness strip's `L:1` read the same in the unit's own
    drawing and in the absolute query: neither the board's `A1-` nor the harness's `WH1-` prefix.
    """
    design = _design()
    (board_unit,) = unit_cables(design.model, design.bu)
    (board_unit_end,) = [end for end in board_unit.ends if end.item == design.strip]
    board_absolute = _by_cable(design)[design.w3]
    (board_absolute_end,) = [end for end in board_absolute.ends if end.item == design.strip]

    (harness_unit,) = unit_cables(design.model, design.hu)
    (harness_unit_end,) = [end for end in harness_unit.ends if end.item == design.harness_strip]
    harness_absolute = _by_cable(design)[design.w1]
    (harness_absolute_end,) = [
        end for end in harness_absolute.ends if end.item == design.harness_strip
    ]

    # One assert over all four readings: a probe that only weakens the fix (dropping unit
    # context entirely, since the real parameter is gone) still shows every one of them here,
    # not just whichever assert pytest happens to reach first.
    assert {
        "board_unit": [pin.marking for pin in board_unit_end.pins],
        "board_absolute": [pin.marking for pin in board_absolute_end.pins],
        "harness_unit": [pin.marking for pin in harness_unit_end.pins],
        "harness_absolute": [pin.marking for pin in harness_absolute_end.pins],
    } == {
        "board_unit": ["L:2"],
        "board_absolute": ["L:2"],
        "harness_unit": ["L:1"],
        "harness_absolute": ["L:1"],
    }


def test_a_top_level_units_outside_end_prints_by_path_not_blank() -> None:
    """`top` is not nested: `M1` at `+EXT` reads `+EXT-M1`, as a top-level unit's lists print it."""
    design = _design()
    (cable,) = unit_cables(design.model, design.top)
    assert cable.designation == "-WH2-W2"
    assert [end.designation for end in cable.ends] == ["-WH2-X3", "+EXT-M1"]
    assert [(core.end_a_designation, core.end_b_designation) for core in cable.cores] == [
        ("-WH2-X3:1", "+EXT-M1:3")
    ]


def test_cable_rows_of_an_unknown_unit_is_refused() -> None:
    """`unit=` naming no unit of the model is a `SchemaError`, not a `KeyError`."""
    design = _design()
    with pytest.raises(SchemaError):
        cable_rows(design.model, design.w1, unit=make_id(Unit, ("nowhere",)))


# -- the absolute queries do not move -----------------------------------------------------------


def test_the_same_cable_read_as_a_harness_cable_still_prints_absolute() -> None:
    """The item document's text, written out by hand: full tags, full location paths."""
    design = _design()
    (cable,) = harness_cables(design.model, design.wh1)
    assert cable.designation == "-WH1-W1"
    assert [end.designation for end in cable.ends] == ["+C1-WH1-X1", "+C1-WH1-X2", "+EXT-M1"]
    assert [(core.end_a_designation, core.end_b_designation) for core in cable.cores] == [
        ("-WH1-X1:1", "-M1:1"),
        ("-WH1-X2:L:1", "-M1:2"),
    ]
    assert cable_rows(design.model, design.w1)[0].cable_designation == "-WH1-W1"


def test_the_other_absolute_queries_stay_absolute() -> None:
    """`all_cables` prints the board cable in full, and no cable is in no unit."""
    design = _design()
    assert top_level_cables(design.model) == ()
    cable = _by_cable(design)[design.w3]
    assert cable.designation == "-A1-W3"
    assert [end.designation for end in cable.ends] == ["+C1-A1-K1", "+C1-A1-S1", "+EXT-M1"]
    assert [(core.end_a_designation, core.end_b_designation) for core in cable.cores] == [
        ("-A1-K1:1", "-M1:4"),
        ("-A1-S1:L:2", "-M1:5"),
    ]


# -- product_designation_in ---------------------------------------------------------------------


def test_product_designation_in_without_context_or_unit_is_product_designation() -> None:
    """Every end item of every cable, and an unplaced item: the item document's own text."""
    design = _design()
    ends = {end.item for cable in all_cables(design.model) for end in cable.ends}
    assert {design.plug, design.strip, design.k1, design.m1} <= ends
    for item in ends:
        assert product_designation_in(design.model, item, None) == product_designation(
            design.model, item
        )
    plant = Plant()
    loose = plant.item("loose", designation="Q9")
    assert product_designation_in(plant.model(), loose, None) == "-Q9"


def test_product_designation_in_prefixes_only_what_is_below_the_context() -> None:
    """From `+C1` an end at `+C1` prints short, `M1` keeps `+EXT`; `unit=` drops the board."""
    design = _design()
    model = design.model
    assert product_designation_in(model, design.k1, design.c1) == "-A1-K1"
    assert product_designation_in(model, design.k1, design.c1, unit=design.bu) == "-K1"
    assert product_designation_in(model, design.k1, None, unit=design.bu) == "+C1-K1"
    assert product_designation_in(model, design.m1, design.c1) == "+EXT-M1"
    assert product_designation_in(model, design.m1, None) == "+EXT-M1"


# -- unit_cable_page_key ------------------------------------------------------------------------


def test_the_unit_cable_page_key_is_one_per_unit_and_cable_and_not_the_items() -> None:
    """Distinct per unit and per cable, equal for equal inputs, never the item document's key."""
    design = _design()
    key = unit_cable_page_key(design.hu, design.w1)
    assert key == unit_cable_page_key(design.hu, design.w1)
    assert key != unit_cable_page_key(design.top, design.w1)
    assert key != unit_cable_page_key(design.hu, design.w2)
    assert key != render_id(design.w1)
    assert key == f"{render_id(design.hu)}~{render_id(design.w1)}"
    assert key.replace(":", "-") == f"unit-{design.hu.value}~item-{design.w1.value}"
