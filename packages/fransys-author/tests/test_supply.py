"""`s.supply(...)`: one `SupplySystem` record, and the refusals authoring owns (Q2)."""

import inspect
import os
from decimal import Decimal
from types import MappingProxyType

import pytest
from fransys_author import AuthorError, Design

from fransys_model.kernel import freeze, merge
from fransys_model.vocab import Current, Earthing, Rail, SupplySystem

_THREE_PHASE = {
    "L1": ("230", 0),
    "L2": ("230", 120),
    "L3": ("230", 240),
    "N": ("0", None),
    "PE": ("0", None),
}
_DC_24 = {"+24V": ("24", None), "0V": ("0", None)}


def _supplies(design: Design) -> list[SupplySystem]:
    return [r for r in design.draft().records() if isinstance(r, SupplySystem)]


def test_the_specs_three_examples_author_and_freeze(parts):
    d = Design(parts)
    d.supply("400V", current="ac", rails=_THREE_PHASE)
    d.supply("24V", current="dc", rails=_DC_24)
    d.supply(
        "DC link",
        current="dc",
        earthing="it",
        rails={"DC+": ("985.5", None), "DC-": ("0", None)},
    )
    model = freeze(merge(parts, d.draft()))
    by_name = {
        s.name: s for s in model.tables["supply_system"].values() if isinstance(s, SupplySystem)
    }
    assert set(by_name) == {"400V", "24V", "DC link"}
    ac, dc, link = by_name["400V"], by_name["24V"], by_name["DC link"]
    assert (ac.current, ac.earthing) == (Current.AC, Earthing.EARTHED)
    assert ac.rails == {
        "L1": Rail(max_v=Decimal(230), phase=0),
        "L2": Rail(max_v=Decimal(230), phase=120),
        "L3": Rail(max_v=Decimal(230), phase=240),
        "N": Rail(max_v=Decimal(0), phase=None),
        "PE": Rail(max_v=Decimal(0), phase=None),
    }
    assert isinstance(ac.rails, frozendict)
    assert (dc.current, dc.earthing) == (Current.DC, Earthing.EARTHED)
    assert dc.rails["+24V"] == Rail(max_v=Decimal(24), phase=None)
    assert (link.current, link.earthing) == (Current.DC, Earthing.IT)
    assert link.rails["DC+"].max_v == Decimal("985.5")


def test_a_decimal_max_v_and_a_negative_dc_rail_are_accepted(parts):
    d = Design(parts)
    d.supply("split", current="dc", rails={"+15V": (Decimal(15), None), "-15V": ("-15", None)})
    (record,) = _supplies(d)
    assert record.rails["-15V"].max_v == Decimal(-15)


def test_six_scopes_declaring_one_supply_give_six_records(parts):
    d = Design(parts)
    for index in range(6):
        d.scope(f"panel{index}").supply("24V", current="dc", rails=_DC_24)
    records = _supplies(d)
    assert len(records) == 6
    assert len({r.id for r in records}) == 6
    assert {r.key for r in records} == {(f"panel{i}", "supply", "24V") for i in range(6)}


def test_one_scope_declaring_a_supply_name_twice_with_different_content_is_refused(parts):
    d = Design(parts)
    d.supply("24V", current="dc", rails=_DC_24)
    with pytest.raises(AuthorError, match="already names a different supply_system record"):
        d.supply("24V", current="dc", earthing="it", rails=_DC_24)


def test_one_scope_declaring_the_same_supply_twice_is_one_record(parts):
    d = Design(parts)
    d.supply("24V", current="dc", rails=_DC_24)
    d.supply("24V", current="dc", rails=_DC_24)
    (record,) = _supplies(d)
    assert record.name == "24V"
    assert record.rails["+24V"] == Rail(max_v=Decimal(24), phase=None)


def _here() -> int:
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    return frame.f_back.f_lineno


def test_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    d.supply("24V", current="dc", rails=_DC_24)
    (record,) = _supplies(d)
    origin = d.draft().origin_of(record.id)
    assert origin is not None
    assert os.path.normcase(origin.file) == os.path.normcase(__file__)
    assert origin.line == line


# Each refusal below has a passing twin: the same call with the one fault removed.


def test_an_ac_rail_above_zero_volts_needs_a_phase(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail 'L1'.*AC at 230 V and needs a phase"):
        d.supply("400V", current="ac", rails={"L1": ("230", None)})
    d.supply("400V", current="ac", rails={"L1": ("230", 0)})
    assert len(_supplies(d)) == 1


def test_an_ac_rail_at_zero_volts_needs_no_phase_and_may_have_one(parts):
    d = Design(parts)
    d.supply("a", current="ac", rails={"N": ("0", None)})
    d.supply("b", current="ac", rails={"N": ("0", 60)})
    phases = {s.name: s.rails["N"].phase for s in _supplies(d)}
    assert phases == {"a": None, "b": 60}


def test_an_ac_phase_must_be_a_multiple_of_sixty(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail 'L2'.*multiple of 60 degrees, not 100"):
        d.supply("400V", current="ac", rails={"L2": ("230", 100)})
    d.supply("400V", current="ac", rails={"L2": ("230", 300)})
    assert len(_supplies(d)) == 1


def test_a_dc_rail_cannot_have_a_phase(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail '\+24V'.*DC and cannot have a phase \(0\)"):
        d.supply("24V", current="dc", rails={"+24V": ("24", 0)})
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    assert len(_supplies(d)) == 1


def test_current_must_be_ac_or_dc(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"'mixed' is not a valid current"):
        d.supply("24V", current="mixed", rails=_DC_24)
    d.supply("24V", current="dc", rails=_DC_24)
    assert len(_supplies(d)) == 1


def test_earthing_must_be_earthed_or_it(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"'floating' is not a valid earthing"):
        d.supply("24V", current="dc", earthing="floating", rails=_DC_24)
    d.supply("24V", current="dc", earthing="it", rails=_DC_24)
    assert len(_supplies(d)) == 1


def test_a_float_max_v_is_refused_naming_the_rail(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail '\+24V' max_v must be a str or Decimal.*24\.0"):
        d.supply("24V", current="dc", rails={"+24V": (24.0, None)})  # ty: ignore[invalid-argument-type] -- a float max_v, testing the "must be a str or Decimal" refusal named in the match
    d.supply("24V", current="dc", rails={"+24V": ("24.0", None)})
    assert len(_supplies(d)) == 1


@pytest.mark.parametrize("phase", [120.0, True])
def test_a_float_or_bool_phase_is_refused(parts, phase):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail 'L2' phase must be an int or None"):
        d.supply("400V", current="ac", rails={"L2": ("230", phase)})
    d.supply("400V", current="ac", rails={"L2": ("230", 120)})
    assert len(_supplies(d)) == 1


def test_a_supply_with_no_rails_is_refused(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"supply '24V' declares no rails"):
        d.supply("24V", current="dc", rails={})
    d.supply("24V", current="dc", rails=_DC_24)
    assert len(_supplies(d)) == 1


@pytest.mark.parametrize("spec", ["24", ("24",), ("24", None, 1)])
def test_a_rail_that_is_not_a_pair_is_refused(parts, spec):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail '\+24V' must be a \(max_v, phase\) pair"):
        d.supply("24V", current="dc", rails={"+24V": spec})
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    assert len(_supplies(d)) == 1


def test_a_refused_supply_writes_no_record(parts):
    d = Design(parts)
    with pytest.raises(AuthorError):
        d.supply("400V", current="ac", rails={"L1": ("230", None)})
    assert _supplies(d) == []
    d.supply("400V", current="ac", rails={"L1": ("230", 0)})
    (record,) = _supplies(d)
    assert record.rails["L1"] == Rail(max_v=Decimal(230), phase=0)


def test_an_ac_rail_cannot_have_a_negative_max_v(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail 'L1'.*AC.*cannot be negative \(-230\)"):
        d.supply("400V", current="ac", rails={"L1": ("-230", 0)})
    d.supply("400V", current="ac", rails={"L1": ("230", 0)})
    (record,) = _supplies(d)
    assert record.rails["L1"].max_v == Decimal(230)


@pytest.mark.parametrize("flag", [True, False])
def test_a_bool_max_v_is_refused(parts, flag):
    d = Design(parts)
    with pytest.raises(
        AuthorError, match=r"rail '\+24V' max_v must be a str or Decimal, not a bool"
    ):
        d.supply("24V", current="dc", rails={"+24V": (flag, None)})
    d.supply("24V", current="dc", rails={"+24V": (Decimal(int(flag)), None)})
    (record,) = _supplies(d)
    assert record.rails["+24V"].max_v == Decimal(int(flag))


@pytest.mark.parametrize("text", ["abc", "", "1,5"])
def test_a_non_numeric_max_v_is_an_author_error(parts, text):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail '\+24V' max_v .* is not a number"):
        d.supply("24V", current="dc", rails={"+24V": (text, None)})
    d.supply("24V", current="dc", rails={"+24V": ("1.5", None)})
    (record,) = _supplies(d)
    assert record.rails["+24V"].max_v == Decimal("1.5")


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity", "sNaN"])
def test_a_non_finite_max_v_is_an_author_error(parts, text):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail '\+24V' max_v must be finite"):
        d.supply("24V", current="dc", rails={"+24V": (text, None)})
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    (record,) = _supplies(d)
    assert record.rails["+24V"].max_v == Decimal(24)


def test_rails_must_be_a_mapping(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rails must be a mapping"):
        d.supply("24V", current="dc", rails=[("+24V", ("24", None))])  # ty: ignore[invalid-argument-type] -- a list of pairs where `rails` needs a mapping, testing the "must be a mapping" refusal
    d.supply("24V", current="dc", rails=MappingProxyType({"+24V": ("24", None)}))
    (record,) = _supplies(d)
    assert set(record.rails) == {"+24V"}


def test_a_rail_potential_must_be_a_str(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"rail potential must be a str, not 24"):
        d.supply("24V", current="dc", rails={24: ("24", None)})  # ty: ignore[invalid-argument-type] -- an int rail key, testing the "rail potential must be a str" refusal
    d.supply("24V", current="dc", rails={"24": ("24", None)})
    (record,) = _supplies(d)
    assert set(record.rails) == {"24"}
