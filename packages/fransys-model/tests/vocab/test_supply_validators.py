"""`SUPPLY_DIFFERS` and `POTENTIAL_IN_TWO_SUPPLIES` (decision model-0075, model review Q2)."""

import dataclasses
from decimal import Decimal

from plant import Plant

from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab import ALL_VALIDATORS, supply_systems
from fransys_model.vocab.enums import Current, Earthing
from fransys_model.vocab.supply_system import Rail, SupplySystem
from fransys_model.vocab.validators.supplies import (
    POTENTIAL_IN_TWO_SUPPLIES,
    SUPPLY_DIFFERS,
    check_supplies,
)


def _dc(max_v: str, phase: int | None = None) -> Rail:
    return Rail(max_v=Decimal(max_v), phase=phase)


def _supply(  # noqa: PLR0913 -- one keyword per thing a test varies
    plant: Plant,
    key: str,
    *,
    name: str = "24V",
    current: Current = Current.DC,
    earthing: Earthing = Earthing.EARTHED,
    rails: dict[str, Rail] | None = None,
) -> Id[SupplySystem]:
    supply = SupplySystem(
        id=make_id(SupplySystem, (key,)),
        key=(key,),
        name=name,
        current=current,
        earthing=earthing,
        rails=frozendict({"+24V": _dc("24"), "0V": _dc("0")} if rails is None else rails),
    )
    plant.add(supply)
    return supply.id


def _of(plant: Plant, code: str) -> list:
    return [f for f in check_supplies(plant.model()) if f.code == code]


def test_two_declarations_with_equal_content_are_one_supply() -> None:
    plant = Plant()
    _supply(plant, "s1")
    _supply(plant, "s2")
    model = plant.model()
    assert len(supply_systems(model)) == 2  # both declarations were seen and compared
    assert check_supplies(model) == ()
    changed = Plant()
    _supply(changed, "s1")
    _supply(changed, "s2", earthing=Earthing.IT)
    assert [f.code for f in check_supplies(changed.model())] == [SUPPLY_DIFFERS]


def test_a_rail_max_v_that_differs_gives_one_error_naming_both_declarations() -> None:
    plant = Plant()
    first = _supply(plant, "s1")
    second = _supply(plant, "s2", rails={"+24V": _dc("28"), "0V": _dc("0")})
    (finding,) = check_supplies(plant.model())
    assert finding.code == SUPPLY_DIFFERS
    assert finding.severity == Severity.ERROR
    assert finding.subjects == tuple(sorted((first, second)))
    assert finding.message == "supplies named '24V' differ in rails: +24V differs"


def test_a_rail_missing_in_one_declaration_is_named() -> None:
    plant = Plant()
    _supply(plant, "s1")
    _supply(plant, "s2", rails={"+24V": _dc("24")})
    (finding,) = _of(plant, SUPPLY_DIFFERS)
    assert "0V is missing in some" in finding.message


def test_declarations_differing_only_in_earthing_give_supply_differs_naming_earthing() -> None:
    plant = Plant()
    _supply(plant, "s1", earthing=Earthing.EARTHED)
    _supply(plant, "s2", earthing=Earthing.IT)
    (finding,) = check_supplies(plant.model())
    assert finding.code == SUPPLY_DIFFERS
    assert finding.message == ("supplies named '24V' differ in earthing: 'earthed', 'it'")


def test_current_and_earthing_differing_name_both_fields() -> None:
    plant = Plant()
    rails = {"+24V": _dc("24", 0), "0V": _dc("0")}  # a phase, so the AC copy is a valid record
    _supply(plant, "s1", rails=rails)
    _supply(plant, "s2", current=Current.AC, earthing=Earthing.IT, rails=rails)
    (finding,) = _of(plant, SUPPLY_DIFFERS)
    assert "differ in current and earthing:" in finding.message
    assert "rails" not in finding.message


def test_current_earthing_and_rails_differing_read_as_a_list() -> None:
    plant = Plant()
    _supply(plant, "s1")
    _supply(
        plant,
        "s2",
        current=Current.AC,
        earthing=Earthing.IT,
        rails={"+24V": _dc("28", 0), "0V": _dc("0")},  # a phase: an AC rail above 0 V needs one
    )
    (finding,) = _of(plant, SUPPLY_DIFFERS)
    assert finding.message == (
        "supplies named '24V' differ in current, earthing and rails: "
        "current 'ac', 'dc'; earthing 'earthed', 'it'; rails +24V differs"
    )


def test_three_declarations_two_agreeing_give_one_finding_with_all_three_subjects() -> None:
    plant = Plant()
    ids = [
        _supply(plant, "s1"),
        _supply(plant, "s2"),
        _supply(plant, "s3", earthing=Earthing.IT),
    ]
    (finding,) = _of(plant, SUPPLY_DIFFERS)
    assert finding.subjects == tuple(sorted(ids))


def test_a_potential_in_two_differently_named_supplies_gives_one_error() -> None:
    plant = Plant()
    first = _supply(plant, "s1", name="24V", rails={"+24V": _dc("24"), "0V": _dc("0")})
    second = _supply(plant, "s2", name="24V-aux", rails={"+24V": _dc("24")})
    (finding,) = check_supplies(plant.model())
    assert finding.code == POTENTIAL_IN_TWO_SUPPLIES
    assert finding.severity == Severity.ERROR
    assert finding.subjects == tuple(sorted((first, second)))
    assert finding.message == (
        "potential '+24V' is a rail of more than one supply: '24V', '24V-aux'"
    )


def test_two_shared_potentials_give_two_findings() -> None:
    plant = Plant()
    _supply(plant, "s1", name="24V")
    _supply(plant, "s2", name="24V-aux")
    assert len(_of(plant, POTENTIAL_IN_TWO_SUPPLIES)) == 2


def test_a_potential_in_two_same_named_declarations_that_differ_is_supply_differs_only() -> None:
    plant = Plant()
    _supply(plant, "s1")
    _supply(plant, "s2", rails={"+24V": _dc("28"), "0V": _dc("0")})
    assert _of(plant, POTENTIAL_IN_TWO_SUPPLIES) == []
    assert len(_of(plant, SUPPLY_DIFFERS)) == 1


def test_can_fail_equal_declarations_do_not_trigger_the_potential_check() -> None:
    plant = Plant()
    _supply(plant, "s1")
    _supply(plant, "s2")
    assert len(supply_systems(plant.model())) == 2
    assert _of(plant, POTENTIAL_IN_TWO_SUPPLIES) == []
    renamed = Plant()
    _supply(renamed, "s1")
    _supply(renamed, "s2", name="24V-aux")
    assert len(_of(renamed, POTENTIAL_IN_TWO_SUPPLIES)) == 2


def test_can_fail_two_supplies_with_distinct_potentials_give_nothing() -> None:
    plant = Plant()
    _supply(plant, "s1", name="24V", rails={"+24V": _dc("24"), "0V": _dc("0")})
    _supply(plant, "s2", name="5V", rails={"+5V": _dc("5"), "GND": _dc("0")})
    model = plant.model()
    assert len(supply_systems(model)) == 2
    assert check_supplies(model) == ()
    shared = Plant()
    _supply(shared, "s1", name="24V", rails={"+24V": _dc("24"), "0V": _dc("0")})
    _supply(shared, "s2", name="5V", rails={"+5V": _dc("5"), "0V": _dc("0")})
    assert [f.code for f in check_supplies(shared.model())] == [POTENTIAL_IN_TWO_SUPPLIES]


def test_no_supply_records_give_no_findings() -> None:
    empty = Plant().model()
    assert len(supply_systems(empty)) == 0
    assert check_supplies(empty) == ()
    one = Plant()
    _supply(one, "s1")
    _supply(one, "s2", earthing=Earthing.IT)
    assert len(check_supplies(one.model())) == 1  # the same check does fire on records


def test_the_findings_surface_through_the_aggregate_validators() -> None:
    """Dropping `check_supplies` from `ALL_VALIDATORS` makes this test fail."""
    plant = Plant()
    _supply(plant, "s1", earthing=Earthing.EARTHED)
    _supply(plant, "s2", earthing=Earthing.IT)
    _supply(plant, "s3", name="24V-aux", rails={"+24V": _dc("24")})
    model = plant.model()
    codes = {f.code for check in ALL_VALIDATORS for f in check(model)}
    assert {SUPPLY_DIFFERS, POTENTIAL_IN_TWO_SUPPLIES} <= codes
    assert check_supplies in ALL_VALIDATORS


def _mixed() -> Plant:
    plant = Plant()
    _supply(plant, "s1")
    _supply(plant, "s2", earthing=Earthing.IT)
    _supply(plant, "s3", name="24V-aux", rails={"+24V": _dc("24")})
    _supply(plant, "s4", name="5V", rails={"+5V": _dc("5")})
    return plant


def test_the_findings_do_not_depend_on_record_insertion_order() -> None:
    plant = _mixed()
    backwards = Plant()
    backwards.add(*reversed(plant.records))
    assert check_supplies(backwards.model()) == check_supplies(plant.model())


def test_the_findings_do_not_depend_on_the_order_of_a_models_tables() -> None:
    model = _mixed().model()
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-supply-validators",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_supplies(backwards) == check_supplies(model)


def test_findings_are_sorted_and_all_errors() -> None:
    findings = check_supplies(_mixed().model())
    assert {f.code for f in findings} == {SUPPLY_DIFFERS, POTENTIAL_IN_TWO_SUPPLIES}
    assert all(f.severity == Severity.ERROR for f in findings)
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
