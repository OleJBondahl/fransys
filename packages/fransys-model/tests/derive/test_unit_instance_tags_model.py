"""UNIT-TAGS UT2, UT3: a floating instance is numbered from its class code, and named by its tag."""

from plant import Plant
from query_builders import make_part

from fransys_model.derive import TOP_LEVEL, bom_lines, unit_release
from fransys_model.derive.baseline_designation import _instance_prefix
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.assigned_unit_tag import AssignedUnitTagFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.validators import check_strip_without_tag


def _tags(plant: Plant, *keys: str) -> list[str | None]:
    model, findings = number(plant.model())
    assert findings == ()
    return [unit_tag(model, make_id(Unit, (key,))) for key in keys]


def test_class_code_rides_on_the_release_and_defaults_to_empty() -> None:
    plant = Plant()
    coded = plant.unit("a", name="board", class_code="U")
    plain = plant.unit("b", name="other")
    model = plant.model()
    assert unit_release(model, coded).class_code == "U"
    assert unit_release(model, plain).class_code == ""


def test_floating_instances_number_from_one_and_skip_a_written_tag() -> None:
    plant = Plant()
    plant.unit("a", name="board", class_code="U", tag="U1")
    plant.unit("b", name="board", class_code="U")
    plant.unit("c", name="board", class_code="U")
    assert _tags(plant, "a", "b", "c") == ["U1", "U2", "U3"]


def test_an_item_of_the_same_class_code_shares_the_count() -> None:
    plant = Plant()
    plant.item("k", part=plant.part("U"))
    plant.item("w", part=plant.part("U"), designation="U2")
    plant.unit("a", name="board", class_code="U")
    assert _tags(plant, "a") == ["U3"]


def test_each_container_counts_on_its_own() -> None:
    plant = Plant()
    cab = plant.unit("cab", name="cabinet", tag="U1")
    plant.unit("a", name="board", class_code="U", parent=cab)
    plant.unit("b", name="board", class_code="U")
    assert _tags(plant, "a", "b") == ["U1", "U2"]


def test_an_instance_of_a_release_without_a_class_code_is_left_alone() -> None:
    plant = Plant()
    plant.unit("a", name="board")
    model, _ = number(plant.model())
    assert unit_tag(model, make_id(Unit, ("a",))) is None
    assert not facets_of(model, AssignedUnitTagFacet)


def test_an_assigned_tag_is_kept_and_counted_by_a_later_run() -> None:
    plant = Plant()
    plant.unit("a", name="board", class_code="U")
    plant.unit("b", name="board", class_code="U")
    once, _ = number(plant.model())
    twice, _ = number(once)
    assert twice is once
    assert [unit_tag(twice, make_id(Unit, (k,))) for k in "ab"] == ["U1", "U2"]


def _cabinet_line_designations(plant: Plant) -> tuple[str, ...]:
    (line,) = [ln for ln in bom_lines(plant.model(), TOP_LEVEL) if ln.part is None]
    return line.designations


def _cabinet(plant: Plant, **unit_args: object) -> None:
    unit = plant.unit("cab", name="cabinet", **unit_args)  # ty: ignore[invalid-argument-type] -- kwargs forwarded
    relay = make_part(plant, "relay", "R-1")
    plant.item("k1", part=relay, designation="K1", unit=unit)
    plant.item("k2", part=relay, designation="K2", unit=unit)


def test_the_bom_unit_line_names_a_tagged_instance_by_its_tag() -> None:
    plant = Plant()
    _cabinet(plant, tag="U3")
    assert _cabinet_line_designations(plant) == ("-U3",)


def test_the_bom_unit_line_of_an_untagged_instance_is_unchanged() -> None:
    plant = Plant()
    _cabinet(plant)
    assert _cabinet_line_designations(plant) == ("-K1", "-K2")


def test_a_baseline_cross_unit_end_names_the_instance_by_its_tags() -> None:
    plant = Plant()
    outer = plant.unit("outer", name="cabinet", tag="U1")
    inner = plant.unit("inner", name="board", parent=outer, tag="U3")
    plant.item("k1", part=make_part(plant, "relay", "R-1"), designation="K1", unit=inner)
    model = plant.model()
    assert _instance_prefix(model, outer, inner) == "-U3/"
    assert _instance_prefix(model, None, inner) == "-U1-U3/"


def _strip(plant: Plant, key: str, *codes: str) -> None:
    """A part-less strip `key` with one terminal per class code in `codes`."""
    strip = plant.item(key)
    for n, code in enumerate(codes, 1):
        term = plant.item(f"{key}-t{n}", parent=strip, part=plant.part(code))
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (key, str(n))),
                key=(key, str(n)),
                subject=term,
                group="",
                index=n,
            )
        )


def _assigned(plant: Plant) -> dict[str, str]:
    model, _ = number(plant.model())
    return {
        facet.subject.value: facet.text
        for facet in facets_of(model, AssignedDesignationFacet).values()
    }


def _strip_text(plant: Plant, key: str) -> str | None:
    return _assigned(plant).get(make_id(Item, (key,)).value)


def test_a_part_less_strip_numbers_from_its_terminals_class_code() -> None:
    plant = Plant()
    _strip(plant, "a", "X")
    _strip(plant, "b", "X")
    assert [_strip_text(plant, k) for k in "ab"] == ["X1", "X2"]


def test_a_part_less_strip_shares_the_count_with_a_tagged_item_of_its_code() -> None:
    plant = Plant()
    plant.item("t", part=plant.part("X"), designation="X1")
    _strip(plant, "a", "X")
    assert _strip_text(plant, "a") == "X2"


def test_a_strip_whose_terminals_disagree_or_that_has_none_is_left_alone() -> None:
    plant = Plant()
    _strip(plant, "mixed", "X", "Y")
    _strip(plant, "empty")
    assert _assigned(plant) == {}


def test_a_floating_item_skips_a_written_instance_tag_of_its_class_code() -> None:
    plant = Plant()
    plant.unit("a", name="board", class_code="U", tag="U1")
    plant.item("k", part=plant.part("U"))
    assert _assigned(plant) == {make_id(Item, ("k",)).value: "U2"}


def test_an_unnumbered_strip_also_gets_the_strip_without_tag_error() -> None:
    plant = Plant()
    _strip(plant, "mixed", "X", "Y")
    _strip(plant, "empty")
    findings = check_strip_without_tag(number(plant.model())[0])
    assert [f.code for f in findings] == ["STRIP_WITHOUT_TAG"] * 2


def test_two_instances_with_one_tag_under_one_parent_are_a_duplicate() -> None:
    plant = Plant()
    cab = plant.unit("cab", name="cabinet", tag="C1")
    plant.unit("a", name="board", tag="U1", parent=cab)
    plant.unit("b", name="board", tag="U1", parent=cab)
    plant.unit("c", name="board", tag="U2", parent=cab)
    _, findings = number(plant.model())
    assert [f.code for f in findings] == ["DESIGNATION_DUPLICATE"] * 2
    assert {f.subjects[0] for f in findings} == {make_id(Unit, (k,)) for k in ("a", "b")}


def test_one_tag_under_two_parents_is_no_duplicate() -> None:
    plant = Plant()
    one = plant.unit("one", name="cabinet", tag="C1")
    two = plant.unit("two", name="cabinet", tag="C2")
    plant.unit("a", name="board", tag="U1", parent=one)
    plant.unit("b", name="board", tag="U1", parent=two)
    assert number(plant.model())[1] == ()
