"""The `supply_system` core kind: `SupplySystem`, `Rail`, `Current`, `Earthing`.

Decision model-0075; `docs/specs/2026-09-25-model-review.md` Q2, Storage. Invented data only.
"""

import dataclasses
import json
from decimal import Decimal
from typing import Any

import pytest

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Origin,
    SchemaError,
    dumps,
    freeze,
    from_data,
    loads,
    make_id,
)
from fransys_model.kernel.encode import to_data
from fransys_model.vocab import Current, Earthing, Rail, SupplySystem, supply_systems
from fransys_model.vocab.supply_system import rail_phase_problem

_ORIGIN = Origin(file="test_supply_system.py", line=1, note="fixture")


def _system(key: str, rails: Any, **fields: Any) -> SupplySystem:
    return SupplySystem(
        id=make_id(SupplySystem, (key,)), key=(key,), name=key, rails=rails, **fields
    )


def _mains() -> SupplySystem:
    return _system(
        "400V",
        frozendict(
            {
                "L1": Rail(max_v=Decimal(230), phase=0),
                "L2": Rail(max_v=Decimal(230), phase=120),
                "N": Rail(max_v=Decimal(0), phase=None),
            }
        ),
        current=Current.AC,
    )


def _control() -> SupplySystem:
    return _system(
        "24V",
        frozendict(
            {
                "+24V": Rail(max_v=Decimal(24), phase=None),
                "0V": Rail(max_v=Decimal(0), phase=None),
            }
        ),
        current=Current.DC,
    )


def _link() -> SupplySystem:
    return _system(
        "DC link",
        frozendict(
            {
                "DC+": Rail(max_v=Decimal("985.5"), phase=None),
                "DC-": Rail(max_v=Decimal(0), phase=None),
            }
        ),
        current=Current.DC,
        earthing=Earthing.IT,
    )


def _freeze(*records: Any) -> Any:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_supply_systems_round_trip_through_canonical_form() -> None:
    """An AC rail at phase 120, a DC rail and an IT system come back equal, digest included."""
    model = _freeze(_mains(), _control(), _link())
    assert from_data(to_data(model)) == model
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.digest == model.digest
    table = supply_systems(reloaded)
    assert table[_mains().id].rails["L2"] == Rail(max_v=Decimal(230), phase=120)
    assert table[_control().id].rails["+24V"].phase is None
    assert table[_link().id].earthing is Earthing.IT
    assert table[_link().id].rails["DC+"].max_v == Decimal("985.5")


def test_the_digest_does_not_depend_on_rail_insertion_order() -> None:
    """The same rails inserted in the reverse order give an equal record and the same digest."""
    forward = _mains()
    backward = dataclasses.replace(forward, rails=frozendict(reversed(forward.rails.items())))
    assert list(backward.rails) != list(forward.rails)
    assert _freeze(forward).digest == _freeze(backward).digest


def test_a_float_max_v_is_refused_at_freeze() -> None:
    """A `float` rail voltage is one `SchemaError` in a `FreezeError`; `Rail` does not check."""
    rails = frozendict({"L1": Rail(max_v=230.0, phase=0)})  # ty: ignore[invalid-argument-type] -- a float max_v; `Rail` itself does not check, so this is meant to survive to `freeze()`
    with pytest.raises(FreezeError) as excinfo:
        _freeze(_system("400V", rails, current=Current.AC))
    (error,) = excinfo.value.errors
    assert type(error) is SchemaError
    assert str(error) == "SupplySystem.rails.L1.max_v: expected Decimal, got float"


def test_a_dict_of_rails_is_refused_at_freeze() -> None:
    """A `dict` for `rails` is one `SchemaError` in a `FreezeError`."""
    with pytest.raises(FreezeError) as excinfo:
        _freeze(_system("400V", {"L1": Rail(max_v=Decimal(230), phase=0)}, current=Current.AC))
    (error,) = excinfo.value.errors
    assert type(error) is SchemaError
    assert str(error) == "SupplySystem.rails: expected frozendict, got dict"


def _rail(max_v: Any, phase: Any) -> Rail:
    return Rail(max_v=max_v, phase=phase)


def _ac(max_v: str, phase: int | None) -> SupplySystem:
    rails = frozendict({"L1": _rail(Decimal(max_v), phase)})
    return _system("400V", rails, current=Current.AC)


def test_an_ac_rail_above_zero_volts_without_a_phase_is_refused_at_construction() -> None:
    """The record refuses it, so no Draft can hold it; the message names supply and rail."""
    with pytest.raises(SchemaError) as excinfo:
        _ac("230", None)
    assert str(excinfo.value) == "supply system '400V' rail 'L1' is AC at 230 V and needs a phase"
    assert excinfo.value.kind == "supply_system"
    assert excinfo.value.record_id == make_id(SupplySystem, ("400V",))


@pytest.mark.parametrize("phase", [45, 30, -30, 61])
def test_a_phase_that_is_not_a_multiple_of_sixty_is_refused(phase: int) -> None:
    """The multiple-of-60 rule holds for every rail and every current."""
    with pytest.raises(SchemaError) as excinfo:
        _ac("230", phase)
    expected = f"supply system '400V' rail 'L1' phase must be a multiple of 60 degrees, not {phase}"
    assert str(excinfo.value) == expected
    with pytest.raises(SchemaError, match="multiple of 60 degrees, not 45"):
        _system("24V", frozendict({"+24V": _rail(Decimal(24), 45)}), current=Current.DC)


def test_the_first_bad_rail_in_potential_order_is_the_one_named() -> None:
    """Two bad rails: the error names the smaller potential whatever the insertion order."""
    rails = frozendict({"L2": _rail(Decimal(230), None), "L1": _rail(Decimal(230), 45)})
    with pytest.raises(SchemaError, match="rail 'L1' phase must be"):
        _system("400V", rails, current=Current.AC)


def test_a_non_rail_value_does_not_stop_checking_later_rails() -> None:
    """A non-`Rail` value is skipped (left for `freeze()`), not a reason to stop checking."""
    rails = frozendict({"L1": "garbage", "L2": _rail(Decimal(230), 45)})
    with pytest.raises(SchemaError, match="rail 'L2' phase must be"):
        _system("400V", rails, current=Current.AC)


def test_the_refusals_holder_is_none_when_the_records_own_id_is_not_a_proper_id() -> None:
    """`holder`'s own type guard: a non-`Id` `self.id` gives `record_id=None`, never itself."""
    bad_id: Any = "not-an-id"
    with pytest.raises(SchemaError) as excinfo:
        SupplySystem(
            id=bad_id,
            key=("k",),
            name="k",
            current=Current.AC,
            rails=frozendict({"L1": _rail(Decimal(230), 45)}),
        )
    assert excinfo.value.record_id is None


def test_rails_the_rule_allows_are_accepted() -> None:
    """AC at 0 V needs no phase, DC needs none, phases 0 and 300 are steps of 60."""
    assert _ac("0", None).rails["L1"].phase is None
    assert _ac("230", 300).rails["L1"].phase == 300
    assert _control().rails["+24V"].phase is None


def _edited_rails(edit: Any) -> dict[str, Any]:
    data = json.loads(dumps(_freeze(_mains())))  # plain dicts: `to_data` gives frozendicts
    edit(data["tables"]["supply_system"][0]["rails"])
    return data


@pytest.mark.parametrize(
    ("edit", "reason"),
    [
        (lambda rails: rails["L2"].update(phase=45), "phase must be a multiple of 60 degrees"),
        (lambda rails: rails["L2"].update(phase=None), "is AC at 230 V and needs a phase"),
    ],
    ids=["phase_45", "phase_removed"],
)
def test_a_decoded_file_with_a_bad_rail_cannot_be_loaded(edit: Any, reason: str) -> None:
    """Decoding builds the record, so its refusal is the file's."""
    data = _edited_rails(edit)
    for load in (from_data, lambda edited: loads(json.dumps(edited))):
        with pytest.raises(FreezeError) as excinfo:
            load(data)
        (error,) = excinfo.value.errors
        assert type(error) is SchemaError
        assert reason in str(error)


def test_rail_phase_problem_says_why_or_none() -> None:
    """Each branch of the predicate, and `None` for anything of the wrong type."""
    assert rail_phase_problem(Current.AC, _rail(Decimal(230), None)) == (
        "is AC at 230 V and needs a phase"
    )
    assert rail_phase_problem(Current.DC, _rail(Decimal(24), 45)) == (
        "phase must be a multiple of 60 degrees, not 45"
    )
    assert rail_phase_problem(Current.AC, _rail(Decimal(0), None)) is None
    assert rail_phase_problem(Current.DC, _rail(Decimal(24), None)) is None
    assert rail_phase_problem(Current.AC, _rail(Decimal(230), 120)) is None
    wrong: list[tuple[Any, Any]] = [
        (Current.AC, _rail(230.0, None)),  # float max_v
        (Current.AC, _rail(Decimal(230), 45.0)),  # float phase
        (Current.AC, _rail(Decimal(230), phase=True)),  # bool phase
        ("ac", _rail(Decimal(230), None)),  # not a Current
    ]
    for current, rail in wrong:
        assert rail_phase_problem(current, rail) is None


def test_rails_are_immutable() -> None:
    """`rails` is a `frozendict` and a `Rail` cannot be assigned to."""
    system = _mains()
    assert type(system.rails) is frozendict
    with pytest.raises(dataclasses.FrozenInstanceError):
        system.rails["L1"].max_v = Decimal(1)  # ty: ignore[invalid-assignment] -- the `Rail` `FrozenInstanceError` this test asserts on
    with pytest.raises(TypeError):
        system.rails["L3"] = Rail(max_v=Decimal(230), phase=240)  # ty: ignore[invalid-assignment] -- the `frozendict` item-assignment `TypeError` this test asserts on, not `Rail`'s own


def test_earthing_defaults_to_earthed() -> None:
    """A supply system built without `earthing` is earthed."""
    assert _mains().earthing is Earthing.EARTHED


def test_equal_content_under_two_keys_is_two_records() -> None:
    """Nothing in the model merges equal supplies: `SUPPLY_DIFFERS` is a later validator."""
    first = _mains()
    second = dataclasses.replace(first, id=make_id(SupplySystem, ("400V-b",)), key=("400V-b",))
    assert len(supply_systems(_freeze(first, second))) == 2
