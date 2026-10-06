"""WP14 tests: what the numbering pass assigns, keeps and reports (design/derive.md)."""

import dataclasses
import re
from decimal import Decimal
from typing import Any

import pytest
from plant import Plant
from query_builders import make_core, make_terminal

from fransys_model.derive import item_designation
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.derive.passes import numbering
from fransys_model.derive.passes.numbering import (
    DESIGNATION_DUPLICATE,
    HARNESS_END_AMBIGUOUS,
    PRODUCT_DESIGNATION_DUPLICATE,
    REFERENCE_DESIGNATION_DUPLICATE,
    number,
)
from fransys_model.kernel import Draft, Id, Model, Origin, Severity, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect, PartCategory
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import facets_of, items
from fransys_model.vocab.templates import Part


def _cable_part(plant: Plant, key: str) -> Id[Part]:
    """A cable part for `key`, class-code empty so it never enters the numbering count
    (RW4b: `is_cable` needs a `CableProductFacet`, not just a `cable` facet).

    `core_colours` starts empty; `query_builders.make_core`'s `_colour_core` grows it to
    match whatever cores the caller adds afterwards, so it always matches the modelled cores.
    """
    part = Part(
        id=make_id(Part, (key, "cable-part")),
        key=(key, "cable-part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description=f"Invented {key}",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        part,
        CableProductFacet(
            id=make_id(CableProductFacet, (key, "product")),
            key=(key, "product"),
            subject=part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    return part.id


def _node(plant: Plant, key: str, aspect: Aspect, *, label: str) -> Id[AspectNode]:
    node = AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=None,
        label=label,
        description="Invented",
    )
    plant.add(node)
    return node.id


def _place(plant: Plant, item: Id[Item], node: Id[AspectNode], key: str) -> Id[Placement]:
    placement = Placement(id=make_id(Placement, (key,)), key=(key,), item=item, node=node)
    plant.add(placement)
    return placement.id


def _designations(model: Model) -> dict[str, str | None]:
    return {item.key[0]: own_designation_or_none(model, item) for item in items(model).values()}


def _item_id(key: str) -> Id[Item]:
    return make_id(Item, (key,))


def _numbered(plant: Plant) -> dict[str, str | None]:
    model, _ = number(plant.model())
    return _designations(model)


# ---- what gets assigned -------------------------------------------------------------------


def test_unnumbered_items_take_the_class_code_and_a_counter_in_key_order() -> None:
    """`K1`, `K2`, `K3` by authoring key, not by anything else."""
    plant = Plant()
    part = plant.part("K")
    for key in ("k-c", "k-a", "k-b"):
        plant.item(key, part=part)
    assert _numbered(plant) == {"k-a": "K1", "k-b": "K2", "k-c": "K3"}


def test_the_format_is_the_letter_and_the_decimal_counter_unpadded() -> None:
    """`W12`, never `W012`."""
    plant = Plant()
    part = plant.part("W")
    for number_ in range(12):
        plant.item(f"w{number_:02d}", part=part)
    assert _numbered(plant)["w11"] == "W12"


def test_each_class_code_has_its_own_counter() -> None:
    """`K1` and `F1` side by side."""
    plant = Plant()
    plant.item("a-relay", part=plant.part("K"))
    plant.item("b-fuse", part=plant.part("F"))
    plant.item("c-relay", part=plant.part("K"))
    assert _numbered(plant) == {"a-relay": "K1", "b-fuse": "F1", "c-relay": "K2"}


def test_a_multi_letter_class_code_has_its_own_counter_from_a_single_letter_one() -> None:
    """`Q`, `Q` and `QA` in one group give `Q1`, `Q2` and `QA1` (designation codes spec C3)."""
    plant = Plant()
    q = plant.part("Q")
    qa = plant.part("QA")
    plant.item("a-q", part=q)
    plant.item("b-q", part=q)
    plant.item("c-qa", part=qa)
    assert _numbered(plant) == {"a-q": "Q1", "b-q": "Q2", "c-qa": "QA1"}


def test_each_parent_has_its_own_counters() -> None:
    """A board's `F1` is independent of the cabinet's `F1` (C3b): the board is read through,
    so its child numbers in the board's own group; the cabinet is a plain item, not read
    through, so its child numbers in the SAME group as every `parent=None` item (its own
    group), not a group of its own."""
    plant = Plant()
    fuse = plant.part("F")
    board = plant.item("board", part=plant.board_part())
    cabinet = plant.item("cabinet")
    plant.item("board-f", part=fuse, parent=board)
    plant.item("cabinet-f", part=fuse, parent=cabinet)
    plant.item("top-f1", part=fuse)
    plant.item("top-f2", part=fuse)
    assert _numbered(plant) == {
        "board": "A1",
        "cabinet": None,
        "board-f": "F1",
        "cabinet-f": "F1",
        "top-f1": "F2",
        "top-f2": "F3",
    }


def test_a_child_of_a_non_read_through_parent_numbers_with_that_parents_own_group() -> None:
    """A suppressor under a contactor prints flat, so it shares the contactor's own group
    (C3b): two contactors' suppressors no longer both land on the bare text `R1`."""
    plant = Plant()
    r = plant.part("R")
    k11 = plant.item("k11")
    k21 = plant.item("k21")
    plant.item("k11-r", part=r, parent=k11)
    plant.item("k21-r", part=r, parent=k21)
    result = _numbered(plant)
    assert {result["k11-r"], result["k21-r"]} == {"R1", "R2"}


def test_authored_designations_are_kept_and_their_strings_are_skipped() -> None:
    """An authored `K5` is skipped as a string: the six others take K1-K4, K6, K7."""
    plant = Plant()
    part = plant.part("K")
    plant.item("authored", part=part, designation="K5")
    for number_ in range(6):
        plant.item(f"n{number_}", part=part)
    result = _numbered(plant)
    assert result["authored"] == "K5"
    assert sorted(str(v) for k, v in result.items() if k != "authored") == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K6",
        "K7",
    ]


def test_a_designation_is_never_parsed_only_compared_as_a_whole_string() -> None:
    """`K01` is not `K1`: it is taken as it is and blocks nothing but itself."""
    plant = Plant()
    part = plant.part("K")
    plant.item("padded", part=part, designation="K01")
    plant.item("plain", part=part)
    assert _numbered(plant) == {"padded": "K01", "plain": "K1"}


def test_a_number_taken_by_another_class_code_is_skipped_too() -> None:
    """The taken set is the sibling group's, whatever the letter: `W1` blocks a `W1`."""
    plant = Plant()
    plant.item("odd", part=plant.part("K"), designation="W1")
    plant.item("cable", part=plant.part("W"))
    assert _numbered(plant) == {"odd": "W1", "cable": "W2"}


def test_terminals_are_never_numbered_and_do_not_use_up_a_number() -> None:
    """A terminal has a part (the terminal block) and no designation of its own.

    A part-less strip takes its terminals' class code (UT3) and so is numbered `X1`; the
    terminal, though it has a part, is never numbered and uses up no number, so `z-other`, the
    strip's other child, takes `X2`. `strip` is a plain item, not board-faceted, so it is not
    read through (C3b): `z-other` numbers in the top-level group.
    """
    plant = Plant()
    block = plant.part("X")
    strip = plant.item("strip")
    terminal = plant.item("a-terminal", part=block, parent=strip)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t", "terminal")),
            key=("t", "terminal"),
            subject=terminal,
            group="L1",
            index=1,
        )
    )
    plant.item("z-other", part=block, parent=strip)
    result = _numbered(plant)
    assert result == {"strip": "X1", "a-terminal": None, "z-other": "X2"}


def test_g11_an_unnumbered_child_of_a_tagged_partless_container_avoids_its_tag() -> None:
    """A part-less container's authored `U1` and its unnumbered `U`-class child's own group
    collide -- gracefully (designer 2026-09-23, G11): the child is numbered `U2`, not `U1`,
    and no finding fires.

    Can-fail (grouping alone reverted to `(item.unit, item.parent)`): the child's own group
    is no longer the container's, so it numbers `U1` instead of `U2`, colliding in VALUE with
    the container's own authored `U1` -- but still `findings == ()` either way, since neither
    item carries a `LOCATION` placement, so `PRODUCT_DESIGNATION_DUPLICATE`'s own gate
    (`_renders_a_location`) excludes both, and `REFERENCE_DESIGNATION_DUPLICATE`'s
    `_renders_a_segment` gate already excluded them for the same reason. The probe is on the
    numbered VALUE, not on a finding appearing.
    """
    plant = Plant()
    container = plant.item("container", designation="U1")
    plant.item("child", part=plant.part("U"), parent=container)
    model, findings = number(plant.model())
    assert _designations(model)["child"] == "U2"
    assert findings == ()


def test_an_item_with_no_part_or_no_class_code_stays_unnumbered() -> None:
    """Nothing to build a designation from: left `None`, no finding of this pass."""
    plant = Plant()
    plant.item("partless")
    plant.item("letterless", part=plant.part(""))
    model, findings = number(plant.model())
    assert _designations(model) == {"partless": None, "letterless": None}
    assert findings == ()


# ---- determinism and identity -------------------------------------------------------------


def _busy(order_seed: int | None) -> Plant:
    plant = Plant()
    parts = [plant.part(letter) for letter in "KFW"]
    board = plant.item("board", designation="A1")
    specs = [(f"i{n}", parts[n % 3], board if n % 2 else None) for n in range(12)]
    specs.append(("authored", parts[0], None))
    if order_seed is not None:
        specs = specs[order_seed:] + specs[:order_seed]
        if order_seed % 2:
            specs.reverse()
    for key, part, parent in specs:
        plant.item(key, part=part, parent=parent, designation="K2" if key == "authored" else None)
    return plant


def test_numbering_is_a_function_of_the_models_content_only() -> None:
    """Models built in other insertion orders are one model (`freeze` sorts): same result."""
    reference, _ = number(_busy(None).model())
    for seed in range(6):
        shuffled, _ = number(_busy(seed).model())
        assert shuffled.digest == reference.digest
        assert _designations(shuffled) == _designations(reference)


def test_a_model_with_nothing_to_number_comes_back_as_the_same_object() -> None:
    """No `evolve` at all, no findings: the second run of the pass puts nothing."""
    plant = Plant()
    plant.item("k1", part=plant.part("K"), designation="K1")
    model = plant.model()
    again, findings = number(model)
    assert again is model
    assert findings == ()
    numbered, _ = number(_busy(None).model())
    second, second_findings = number(numbered)
    assert second is numbered
    assert second_findings == ()


def test_numbering_leaves_the_item_alone_and_puts_one_assigned_designation_facet() -> None:
    """Other tables are the model's own objects; the item is unchanged (its tag stays `None`)
    and its number lives in one `facet.assigned_designation`."""
    plant = Plant()
    part = plant.part("K")
    item = plant.item("k1", part=part)
    plant.port(plant.function(item, "fn"), "1")
    model = plant.model()
    numbered, _ = number(model)
    assert numbered.tables["part"] is model.tables["part"]
    assert numbered.tables["port"] is model.tables["port"]
    before, after = items(model)[_item_id("k1")], items(numbered)[_item_id("k1")]
    assert after == before
    assert after.tag is None
    assert facets_of(model, AssignedDesignationFacet) == {}
    (assigned,) = facets_of(numbered, AssignedDesignationFacet).values()
    assert (assigned.subject, assigned.text, assigned.key) == (
        _item_id("k1"),
        "K1",
        ("k1", "assigned_designation"),
    )
    assert item_designation(numbered, _item_id("k1")) == "K1"
    assert numbered.digest != model.digest


def test_a_numbered_item_keeps_the_origin_it_was_authored_with() -> None:
    """Errors about it still cite the author's line, not the pass."""
    plant = Plant()
    part = plant.part("K")
    draft = Draft()
    first, second = Origin(file="a.py", line=3, note="one"), Origin(file="b.py", line=9, note="two")
    draft.extend(plant.records, origin=first)
    later = Plant()
    later.item("k-a", part=part)
    draft.add(later.records[0], origin=second)
    other = Plant()
    other.item("k-b", part=part)
    draft.add(other.records[0], origin=first)
    model = freeze(draft)
    numbered, _ = number(model)
    for key, origin in (("k-a", second), ("k-b", first)):
        assert numbered.origin_of(_item_id(key)) == origin
    assert _designations(numbered) == {"k-a": "K1", "k-b": "K2"}


# ---- DESIGNATION_DUPLICATE ----------------------------------------------------------------


def test_two_authored_duplicates_are_one_error_each_and_are_kept() -> None:
    """One finding per item, subject that item; the pass reports, it does not resolve.

    Both items also share `unit=None` and print the same bare, unplaced text `-K1`, so
    `PRODUCT_DESIGNATION_DUPLICATE` fires too, alongside the two `DESIGNATION_DUPLICATE`
    findings (spec `2026-09-23-designation-codes.md` C3b's amendment): unplaced items with
    one designation in one unit instance print alike.
    """
    plant = Plant()
    part = plant.part("K")
    plant.item("k-a", part=part, designation="K1")
    plant.item("k-b", part=part, designation="K1")
    model, findings = number(plant.model())
    designation_findings = [f for f in findings if f.code == DESIGNATION_DUPLICATE]
    assert [f.code for f in designation_findings] == [DESIGNATION_DUPLICATE] * 2
    assert {f.subjects for f in designation_findings} == {
        (_item_id("k-a"),),
        (_item_id("k-b"),),
    }
    assert {f.severity for f in findings} == {Severity.ERROR}
    assert [f.code for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE] == [
        PRODUCT_DESIGNATION_DUPLICATE
    ]
    assert _designations(model) == {"k-a": "K1", "k-b": "K1"}


def test_three_duplicates_are_three_findings() -> None:
    """One `DESIGNATION_DUPLICATE` per colliding item, plus one `PRODUCT_DESIGNATION_DUPLICATE`
    for the one bare, unplaced, same-unit group all three share (spec amendment)."""
    plant = Plant()
    for key in ("a", "b", "c"):
        plant.item(key, designation="F1")
    assert len(number(plant.model())[1]) == 4


def test_the_same_designation_under_different_parents_is_no_duplicate() -> None:
    """A board's `F1` and the cabinet's `F1` (design/examples.md 11)."""
    plant = Plant()
    board, cabinet = plant.item("board", part=plant.board_part()), plant.item("cabinet")
    plant.item("board-f", parent=board, designation="F1")
    plant.item("cabinet-f", parent=cabinet, designation="F1")
    assert number(plant.model())[1] == ()


def test_a_duplicate_is_found_across_class_codes_as_a_whole_string() -> None:
    """Whatever the parts say, `K1` twice is twice: 2 `DESIGNATION_DUPLICATE`, plus 1
    `PRODUCT_DESIGNATION_DUPLICATE` for the shared bare, unplaced, same-unit text (spec
    amendment)."""
    plant = Plant()
    plant.item("a", part=plant.part("K"), designation="K1")
    plant.item("b", part=plant.part("F"), designation="K1")
    assert len(number(plant.model())[1]) == 3


def _placed_terminal(plant: Plant, key: str, node: Id[AspectNode], *, parent: str | None) -> None:
    """A terminal `L1:1` with no `designation` field (as authored), placed at `node`."""
    item = plant.item(key, parent=None if parent is None else _item_id(parent))
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, (key, "terminal")),
            key=(key, "terminal"),
            subject=item,
            group="L1",
            index=1,
        )
    )
    _place(plant, item, node, f"p-{key}")


def test_two_strips_terminals_l1_1_under_one_function_group_are_not_a_duplicate() -> None:
    """Decision model-0064: `=G-X1:L1:1` and `=G-X2:L1:1` differ, so nothing collides."""
    plant = Plant()
    group = _node(plant, "g", Aspect.FUNCTION, label="G")
    for strip in ("x1", "x2"):
        plant.item(strip, designation=strip.upper())
        _placed_terminal(plant, f"{strip}-t", group, parent=strip)
    model, findings = number(plant.model())
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []
    assert numbering.reference_designation(model, _item_id("x1-t")) == "=G-X1:L1:1"
    assert numbering.reference_designation(model, _item_id("x2-t")) == "=G-X2:L1:1"


def test_can_fail_two_parentless_terminals_at_one_group_read_alike_and_are_an_error() -> None:
    """Terminals are compared now: two with no strip both read `=G-L1:1` (model-0064, R2)."""
    plant = Plant()
    group = _node(plant, "g", Aspect.FUNCTION, label="G")
    _placed_terminal(plant, "t1", group, parent=None)
    _placed_terminal(plant, "t2", group, parent=None)
    _, findings = number(plant.model())
    (finding,) = [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE]
    assert finding.severity is Severity.ERROR
    assert set(finding.subjects) == {_item_id("t1"), _item_id("t2")}
    assert "'=G-L1:1'" in finding.message


def _twin_strips(plant: Plant, *, locations: tuple[str, str]) -> None:
    """Two unit instances, each a strip `X1` at `locations[i]` and an unplaced terminal `L1:1`."""
    for index, label in enumerate(locations):
        unit = plant.unit(f"u{index}", name="cab")
        strip = f"x1-{index}"
        plant.item(strip, designation="X1", unit=unit)
        _place(
            plant,
            _item_id(strip),
            _node(plant, f"loc{index}", Aspect.LOCATION, label=label),
            f"p{index}",
        )
        terminal = plant.item(f"t-{index}", parent=_item_id(strip), unit=unit)
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (f"t-{index}", "terminal")),
                key=(f"t-{index}", "terminal"),
                subject=terminal,
                group="L1",
                index=1,
            )
        )


def test_twin_terminals_with_only_a_location_through_their_strips_do_not_collide() -> None:
    """`+C1-X1:L1:1` and `+C2-X1:L1:1`: compared with the strip's location, and distinct."""
    plant = Plant()
    _twin_strips(plant, locations=("C1", "C2"))
    _, findings = number(plant.model())
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_can_fail_twin_terminals_through_strips_at_one_location_are_an_error() -> None:
    """Both strips at `+C1`: the terminals read `+C1-X1:L1:1` alike and are reported."""
    plant = Plant()
    _twin_strips(plant, locations=("C1", "C1"))
    _, findings = number(plant.model())
    messages = [f.message for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE]
    assert any("'+C1-X1:L1:1'" in message for message in messages)


@pytest.mark.parametrize("scenario", ["strip-unplaced", "strip-placed", "under-undesignated-board"])
def test_a_placed_terminal_whose_strip_cannot_print_is_left_out_not_a_crash(scenario: str) -> None:
    """A strip with no designation (no part, or the board above it has none) cannot be printed.

    v0.3.1 skipped every terminal, so `number()` returned; the terminal is now compared only
    when its reference can be printed (decision model-0064), else `item_designation` would
    raise. The missing tag is `ITEM_WITHOUT_PART`'s to report, not this pass's.
    """
    plant = Plant()
    group = _node(plant, "g", Aspect.FUNCTION, label="G")
    parent: str | None = None
    if scenario == "under-undesignated-board":
        board_part = Part(
            id=make_id(Part, ("board-part",)),
            key=("board-part",),
            mpn="MPN-board",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.BOARD,
            class_code="",
        )
        plant.add(
            board_part,
            PcbFacet(
                id=make_id(PcbFacet, ("board-part", "pcb")),
                key=("board-part", "pcb"),
                subject=board_part.id,
                revision="A",
            ),
        )
        parent = "board"
        plant.item(parent, part=board_part.id)
    strip = plant.item("strip", parent=None if parent is None else _item_id(parent))
    if scenario == "strip-placed":
        _place(plant, strip, group, "p-strip")
    _placed_terminal(plant, "t1", group, parent="strip")
    _, findings = number(plant.model())
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_terminals_without_a_placement_are_still_left_out_of_the_duplicate_check() -> None:
    """No `=`/`+` placement means no fuller text to collide on, terminal or not."""
    plant = Plant()
    terminals = []
    for key in ("t1", "t2"):
        terminals.append(plant.item(key, designation="L1:1"))
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (key, "terminal")),
                key=(key, "terminal"),
                subject=terminals[-1],
                group="L1",
                index=1,
            )
        )
    assert number(plant.model())[1] == ()


# ---- PRODUCT_DESIGNATION_DUPLICATE ---------------------------------------------------------


def test_product_designation_duplicate_for_one_location_two_function_aspects() -> None:
    """Two authored `-K1`s at one location, in different function loops (C3b): one
    `PRODUCT_DESIGNATION_DUPLICATE`, subjects both items -- and no
    `REFERENCE_DESIGNATION_DUPLICATE`, since the full `=`-qualified text still differs."""
    plant = Plant()
    item_a = plant.item("k1-a", designation="K1")
    item_b = plant.item("k1-b", designation="K1")
    location = _node(plant, "loc", Aspect.LOCATION, label="C1")
    fn_a = _node(plant, "fn-a", Aspect.FUNCTION, label="A1")
    fn_b = _node(plant, "fn-b", Aspect.FUNCTION, label="A2")
    _place(plant, item_a, location, "p-loc-a")
    _place(plant, item_b, location, "p-loc-b")
    _place(plant, item_a, fn_a, "p-fn-a")
    _place(plant, item_b, fn_b, "p-fn-b")
    _, findings = number(plant.model())
    product_findings = [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE]
    assert len(product_findings) == 1
    (finding,) = product_findings
    assert set(finding.subjects) == {item_a, item_b}
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_product_designation_duplicate_for_two_unplaced_items_in_one_unit_instance() -> None:
    """Two authored `-K1`s, no `LOCATION` placement, both in the SAME unit instance: they
    print the same bare text there, so `PRODUCT_DESIGNATION_DUPLICATE` fires (spec
    `2026-09-23-designation-codes.md` C3b's amendment)."""
    plant = Plant()
    unit = plant.unit("cab")
    item_a = plant.item("k1-a", designation="K1", unit=unit)
    item_b = plant.item("k1-b", designation="K1", unit=unit)
    _, findings = number(plant.model())
    product_findings = [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE]
    assert len(product_findings) == 1
    (finding,) = product_findings
    assert set(finding.subjects) == {item_a, item_b}


def test_no_product_designation_duplicate_across_two_unit_instances() -> None:
    """The same two authored `-K1`s, no `LOCATION` placement, but each in a DIFFERENT unit
    instance: two instances of one unit number alike on purpose (units spec U7), so no
    finding fires."""
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    plant.item("k1-a", designation="K1", unit=unit_a)
    plant.item("k1-b", designation="K1", unit=unit_b)
    _, findings = number(plant.model())
    assert [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE] == []


# ---- HARNESS_END_AMBIGUOUS -------------------------------------------------------------------


def test_harness_end_ambiguous_for_a_cable_between_two_unplaced_unit_instances() -> None:
    """Two unit instances' unplaced `X1` strips print the same bare text `"-X1"` -- fine on
    their own, no `PRODUCT_DESIGNATION_DUPLICATE` (units spec U7,
    `test_no_product_designation_duplicate_across_two_unit_instances` above) -- but a
    top-level cable that joins them draws two identically-titled ends in one picture:
    `HARNESS_END_AMBIGUOUS` (designer ruling 2026-09-24), subjects the cable and both strips."""
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    x1_a = plant.item("x1-a", designation="X1", unit=unit_a)
    x1_b = plant.item("x1-b", designation="X1", unit=unit_b)
    l1_a = make_terminal(plant, "x1-a", "t1", group="L", index=1)
    l1_b = make_terminal(plant, "x1-b", "t1", group="L", index=1)
    cable = plant.item("w1", designation="W1", part=_cable_part(plant, "w1"))
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core", cable, (l1_a.external, l1_b.external), index=1)
    _, findings = number(plant.model())
    ambiguous = [f for f in findings if f.code == HARNESS_END_AMBIGUOUS]
    assert len(ambiguous) == 1
    (finding,) = ambiguous
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {cable, x1_a, x1_b}
    assert finding.message == (
        "two ends of -W1 print '-X1'; place the unit instances at locations or tag the strips apart"
    )


def _undesignated_ancestor(plant: Plant, shape: str) -> Id[Item]:
    """An item that is structurally a harness or a board but has no designation of its own.

    `"harness"`: a plain, untagged item with a cable-faceted child (H2). `"board"`: an
    untagged item whose part carries the `pcb` facet but an empty class code, so numbering
    never tags it either (as `test_a_placed_terminal_whose_strip_cannot_print_is_left_out_
    not_a_crash`'s `"under-undesignated-board"` scenario builds it).
    """
    if shape == "harness":
        harness = plant.item("w0")
        cable_part = plant.part("W")
        plant.add(
            CableProductFacet(
                id=make_id(CableProductFacet, ("w0c", "product")),
                key=("w0c", "product"),
                subject=cable_part,
                core_colours=(),
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            )
        )
        cable = plant.item("w0c", parent=harness, part=cable_part)
        plant.add(
            CableFacet(
                id=make_id(CableFacet, ("w0c", "cable")),
                key=("w0c", "cable"),
                subject=cable,
                length_mm=1,
            )
        )
        return harness
    board_part = Part(
        id=make_id(Part, ("board-part",)),
        key=("board-part",),
        mpn="MPN-board",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.BOARD,
        class_code="",
    )
    plant.add(
        board_part,
        PcbFacet(
            id=make_id(PcbFacet, ("board-part", "pcb")),
            key=("board-part", "pcb"),
            subject=board_part.id,
            revision="A",
        ),
    )
    return plant.item("board", part=board_part.id)


@pytest.mark.parametrize("shape", ["harness", "board"])
def test_two_colliding_children_of_an_undesignated_ancestor_are_left_out(shape: str) -> None:
    """model-0107: an ancestor with no designation of its own leaves its children out of both
    `REFERENCE_DESIGNATION_DUPLICATE` and `PRODUCT_DESIGNATION_DUPLICATE` -- `item_designation`
    would raise walking the ancestor's own label (`_ancestor_label`), so `can_print_designation`
    excludes them rather than the pass raising or comparing them. Two children with the SAME
    authored tag, both placed at one `LOCATION` node, would otherwise collide on both checks;
    `DESIGNATION_DUPLICATE` still fires, since it never reads the ancestor's designation at all.
    """
    plant = Plant()
    ancestor = _undesignated_ancestor(plant, shape)
    location = _node(plant, "loc", Aspect.LOCATION, label="C1")
    child_a = plant.item("child-a", parent=ancestor, designation="X1")
    child_b = plant.item("child-b", parent=ancestor, designation="X1")
    _place(plant, child_a, location, "p-a")
    _place(plant, child_b, location, "p-b")
    _, findings = number(plant.model())
    assert len([f for f in findings if f.code == DESIGNATION_DUPLICATE]) == 2
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []
    assert [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE] == []


def test_product_designation_duplicate_ignores_unit_at_one_location_two_functions() -> None:
    """Two DIFFERENT unit instances, each `K1`, at one shared `LOCATION` node but each in its
    own `FUNCTION` node: `PRODUCT_DESIGNATION_DUPLICATE` compares by location text alone,
    `unit` ignored (decision model-0044) -- one finding, exact message. The function segment
    differs, so the fuller `REFERENCE_DESIGNATION_DUPLICATE` text does not collide.
    """
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    item_a = plant.item("k1-a", designation="K1", unit=unit_a)
    item_b = plant.item("k1-b", designation="K1", unit=unit_b)
    location = _node(plant, "loc", Aspect.LOCATION, label="C1")
    fn_a = _node(plant, "fn-a", Aspect.FUNCTION, label="FA")
    fn_b = _node(plant, "fn-b", Aspect.FUNCTION, label="FB")
    _place(plant, item_a, location, "p-loc-a")
    _place(plant, item_b, location, "p-loc-b")
    _place(plant, item_a, fn_a, "p-fn-a")
    _place(plant, item_b, fn_b, "p-fn-b")
    _, findings = number(plant.model())
    product_findings = [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE]
    (finding,) = product_findings
    assert set(finding.subjects) == {item_a, item_b}
    assert finding.message == "product designation '+C1-K1' is shared by k1-a, k1-b"
    assert [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE] == []


def test_reference_designation_duplicate_fires_model_wide_across_two_unit_instances() -> None:
    """Two DIFFERENT unit instances, each `K1`, placed at the SAME `FUNCTION` node and nowhere
    else: `REFERENCE_DESIGNATION_DUPLICATE` fires model-wide, "units or not" (`number`'s own
    docstring) -- unlike `PRODUCT_DESIGNATION_DUPLICATE`, which never fires here since neither
    item carries a `LOCATION` placement (`_renders_a_location` excludes both, and each is in a
    different unit, so `by_unit_text` never groups them together either).
    """
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    item_a = plant.item("k1-a", designation="K1", unit=unit_a)
    item_b = plant.item("k1-b", designation="K1", unit=unit_b)
    function = _node(plant, "fn", Aspect.FUNCTION, label="FA")
    _place(plant, item_a, function, "p-fn-a")
    _place(plant, item_b, function, "p-fn-b")
    _, findings = number(plant.model())
    reference_findings = [f for f in findings if f.code == REFERENCE_DESIGNATION_DUPLICATE]
    (finding,) = reference_findings
    assert set(finding.subjects) == {item_a, item_b}
    assert finding.message == "reference designation '=FA-K1' is shared by k1-a, k1-b"
    assert [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE] == []


def test_findings_are_sorted_and_messages_never_print_an_id() -> None:
    """Sorted by `(code, subjects, message)`; messages name designations and keys."""
    plant = Plant()
    for key in ("a", "b", "c", "d"):
        plant.item(key, designation="K1" if key < "c" else "K2")
    findings = number(plant.model())[1]
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    for finding in findings:
        assert re.search(r"K[12]", finding.message)
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_findings_are_sorted_across_parents_not_grouped_by_them() -> None:
    """Several parents, each with a collision: the order is the sort key's, not the walk's.

    `p0`..`p3` are plain items, not board-faceted, so none is read through (C3b): all 8
    children share one top-level group, giving 8 `DESIGNATION_DUPLICATE` findings, one per
    item. None is placed in the location aspect, so none is compared by
    `PRODUCT_DESIGNATION_DUPLICATE`'s location-wide branch, but all 8 share `unit=None` and
    the same bare, unplaced text `-K1`, so they fall into one `by_unit_text` group and add
    one more `PRODUCT_DESIGNATION_DUPLICATE` (spec amendment) -- 9 findings, not 8.
    """
    plant = Plant()
    parents = [plant.item(f"p{n}") for n in range(4)]
    for number_, parent in enumerate(parents):
        for twin in ("a", "b"):
            plant.item(f"i{number_}{twin}", parent=parent, designation="K1")
    findings = number(plant.model())[1]
    assert len(findings) == 9
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def _backwards(model: Model) -> Model:
    """The same records with every table in the opposite order, under another digest."""
    return dataclasses.replace(
        model,
        digest="reversed-tables-test-numbering-model",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )


def test_numbering_does_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards: the same designations and the same findings.

    `dup-a`/`dup-b` collide on `DESIGNATION_DUPLICATE` (2 findings) and, sharing `unit=None`
    and the bare, unplaced text `-Z9`, on `PRODUCT_DESIGNATION_DUPLICATE` too (1 more, spec
    amendment): 3 findings.
    """
    plant = _busy(None)
    for key in ("dup-a", "dup-b"):
        plant.item(key, designation="Z9")
    model = plant.model()
    forward, forward_findings = number(model)
    backward, backward_findings = number(_backwards(model))
    assert _designations(backward) == _designations(forward)
    assert backward_findings == forward_findings
    assert len(forward_findings) == 3


def test_numbering_is_one_evolve_and_every_item_still_cites_its_own_origin() -> None:
    """Twenty items, twenty origins, one `evolve` call: the origins are put back afterwards."""
    plant = Plant()
    part = plant.part("K")
    draft = Draft()
    draft.add(plant.records[0], origin=Origin(file="parts.py", line=1, note="part"))
    origins = {}
    for index in range(20):
        key = f"k{index:02d}"
        origins[key] = Origin(file="plant.py", line=100 + index, note=key)
        scratch = Plant()
        scratch.item(key, part=part)
        draft.add(scratch.records[0], origin=origins[key])
    model = freeze(draft)
    calls = []
    real = numbering.evolve

    def counting(*args: Any, **kwargs: Any) -> Model:
        calls.append(1)
        return real(*args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(numbering, "evolve", counting)
        numbered, _ = number(model)
    assert len(calls) == 1
    for key, origin in origins.items():
        assert numbered.origin_of(_item_id(key)) == origin
    assert len(_designations(numbered)) == 20


# ---- an accessory prints its parent's designation (model-0058) ----


def test_a_child_of_a_partless_parent_numbers_as_today() -> None:
    """A parent with no part passes nothing down, even with a tag: the child takes `F1`."""
    plant = Plant()
    holder = plant.item("holder", designation="F11")
    plant.item("link", part=plant.part("F"), parent=holder)
    assert _numbered(plant) == {"holder": "F11", "link": "F1"}


def test_a_child_of_a_tagged_holder_stays_unnumbered_and_uses_no_counter() -> None:
    """A part-bearing child of a tagged holder stays `None`, and a top-level `F` item still
    gets `F1`: the child used up no number."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    plant.item("link", part=plant.part("F"), parent=holder)
    plant.item("other", part=plant.part("F"))
    assert _numbered(plant) == {"holder": "F11", "link": None, "other": "F1"}


def test_a_child_of_an_untagged_holder_with_a_class_code_stays_unnumbered() -> None:
    """Numbering will tag the holder (`H1`), so its child is left `None` (the class-code rule)."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"))
    plant.item("link", part=plant.part("F"), parent=holder)
    assert _numbered(plant) == {"holder": "H1", "link": None}


def test_a_child_of_a_holder_with_no_tag_and_no_class_code_numbers_as_today() -> None:
    """A holder whose part has an empty class code and no tag is never designated: the child
    takes `F1`."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part(""))
    plant.item("link", part=plant.part("F"), parent=holder)
    assert _numbered(plant) == {"holder": None, "link": "F1"}


def test_a_child_of_a_board_numbers_as_today() -> None:
    """A board is read through, not a holder: its part-bearing child takes `F1` in the board."""
    plant = Plant()
    board = plant.item("board", part=plant.board_part())
    plant.item("link", part=plant.part("F"), parent=board)
    assert _numbered(plant) == {"board": "A1", "link": "F1"}


def test_a_child_of_a_harness_numbers_as_today() -> None:
    """A harness (an item with a cable child) is read through, not a holder: the child takes
    `F1` in the harness."""
    plant = Plant()
    harness = plant.item("harness", part=plant.part("H"), designation="W3")
    cable = plant.item("cable", parent=harness, part=_cable_part(plant, "cable"))
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("cable", "cable")),
            key=("cable", "cable"),
            subject=cable,
            length_mm=1,
        )
    )
    plant.item("link", part=plant.part("F"), parent=harness)
    assert _numbered(plant) == {"harness": "W3", "cable": None, "link": "F1"}


def test_a_board_child_of_a_designated_device_numbers_as_today() -> None:
    """A board under a tagged device is no accessory: it takes `A1`, or its components could
    never print (`item_designation` refuses a board with no designation)."""
    plant = Plant()
    device = plant.item("device", part=plant.part("D"), designation="A5")
    plant.item("card", part=plant.board_part(), parent=device)
    assert _numbered(plant) == {"device": "A5", "card": "A1"}


def test_a_harness_child_of_a_designated_device_numbers_as_today() -> None:
    """A harness (an item with a cable child) under a tagged device is no accessory: `W1`."""
    plant = Plant()
    device = plant.item("device", part=plant.part("D"), designation="A5")
    harness = plant.item("harness", part=plant.part("W"), parent=device)
    cable = plant.item("cable", parent=harness, part=_cable_part(plant, "cable"))
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("cable", "cable")),
            key=("cable", "cable"),
            subject=cable,
            length_mm=1,
        )
    )
    assert _numbered(plant) == {"device": "A5", "harness": "W1", "cable": None}


def test_a_child_of_a_terminal_parent_numbers_as_today() -> None:
    """A terminal is never a holder, even with a part with a class code: the child takes `F1`."""
    plant = Plant()
    terminal = plant.item("terminal", part=plant.part("X"))
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t", "terminal")),
            key=("t", "terminal"),
            subject=terminal,
            group="L1",
            index=1,
        )
    )
    plant.item("child", part=plant.part("F"), parent=terminal)
    assert _numbered(plant) == {"terminal": None, "child": "F1"}


def test_a_child_with_an_authored_tag_keeps_it_and_is_no_accessory() -> None:
    """The authored `F5` stays; only the untagged sibling under the same holder stays `None`."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    plant.item("tagged", part=plant.part("F"), parent=holder, designation="F5")
    plant.item("plain", part=plant.part("F"), parent=holder)
    assert _numbered(plant) == {"holder": "F11", "tagged": "F5", "plain": None}


def test_a_child_with_a_function_numbers_as_today() -> None:
    """A child that has a function of its own is a real device, not an accessory: `F1`."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    plant.function(link, "fn")
    assert _numbered(plant) == {"holder": "F11", "link": "F1"}


def test_a_tagged_holder_and_its_child_at_one_location_raise_no_finding() -> None:
    """Both placed at one location node: the child prints the holder's text but carries no
    designation of its own, so no duplicate finding of any kind fires.

    Expected to pass on the base as well: there the child numbers `F1`, never `F11`.
    """
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    location = _node(plant, "loc", Aspect.LOCATION, label="C1")
    _place(plant, holder, location, "p-holder")
    _place(plant, link, location, "p-link")
    _, findings = number(plant.model())
    assert findings == ()


def test_a_child_of_an_accessory_child_also_stays_unnumbered() -> None:
    """The chain holds: `sub` under `link` under the tagged holder stays `None` as well, since
    `link`'s part has a class code (it counts as designated)."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    plant.item("sub", part=plant.part("Q"), parent=link)
    assert _numbered(plant) == {"holder": "F11", "link": None, "sub": None}
