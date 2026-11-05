"""The breaking capacity of a `[function.block]` in a part file (parts-0015, model-0369)."""

from decimal import Decimal

import fransys_parts
import pytest
from part_roots import part_root

from fransys_model.elecdef import Breaker, Current, Fuse, Quantity, Unit
from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import BlockFacet, facets_of

_HEAD = """schema = 2

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"
"""
_FUNCTION = """
[[function]]
name = "f1"
kind = "generic"
ports = [{ name = "1", role = "generic" }]
"""
_PROTECTION = _FUNCTION.replace('kind = "generic"', 'kind = "protection"')
_AC = '{ max = "10000 A", at = ["AC", "400 V"] }'
_DC = '{ max = "15000 A", at = ["DC", "1000 V", "15 ms"] }'
_MIN = '{ min = "4000 A" }'


def _block(figures, kind="fuse", key="breaking_capacity"):
    value = f"[{figures}]" if key == "breaking_capacity" else figures
    return _HEAD + _PROTECTION + f'\n[function.block]\ntype = "{kind}"\n{key} = {value}\n'


def _lint(tmp_path, text):
    return fransys_parts.lint(part_root(tmp_path, text))


def _stored(tmp_path, text):
    model = freeze(fransys_parts.load_path(part_root(tmp_path, text)))
    (facet,) = facets_of(model, BlockFacet).values()
    return facet.block


def test_a_fuse_breaking_capacity_arrives_as_a_fuse_block(tmp_path):
    block = _stored(tmp_path, _block(f"{_AC}, {_DC}, {_MIN}"))
    assert isinstance(block, Fuse)
    ac, dc, minimum = block.breaking_capacity
    assert ac.max == Quantity(Decimal(10000), Unit.A)
    assert dc.at.get(Current) is Current.DC
    assert dc.at.get(Unit.MS.kind) == Quantity(Decimal(15), Unit.MS)
    assert minimum.min == Quantity(Decimal(4000), Unit.A)


def test_a_part_level_block_arrives_as_the_blockfacet_of_its_one_template(tmp_path):
    model = freeze(fransys_parts.load_path(part_root(tmp_path, _HEAD + f'\n[block]\ntype = "fuse"\nbreaking_capacity = [{_MIN}]\n' + _FUNCTION)))
    (facet,) = facets_of(model, BlockFacet).values()
    assert isinstance(facet.block, Fuse)
    assert facet.block.breaking_capacity[0].min == Quantity(Decimal(4000), Unit.A)
    assert facet.key[-2:] == ("f1", "block")


def test_a_part_level_block_on_a_part_with_two_functions_is_refused(tmp_path):
    text = (
        _HEAD
        + f'\n[block]\ntype = "fuse"\nbreaking_capacity = [{_MIN}]\n'
        + _FUNCTION
        + _FUNCTION.replace("f1", "f2").replace('name = "1"', 'name = "2"')
    )
    (refused,) = [f for f in _lint(tmp_path, text) if f.severity is Severity.ERROR]
    assert refused.code == "RATING_VALUE_INVALID"
    assert "part X-1 has 2 functions" in refused.message
    assert "state [block] per pole" in refused.message


def test_a_part_block_takes_the_same_field_checks(tmp_path):
    text = _HEAD + '\n[block]\ntype = "mcb"\nbreaking_capacity = [{ min = "1 A" }]\n' + _FUNCTION
    assert [f.code for f in _lint(tmp_path, text) if f.severity is Severity.ERROR] == ["FIELD_UNKNOWN"]
    assert "RATING_VALUE_INVALID" in {f.code for f in _lint(tmp_path, text.replace("mcb", "fuse").replace('{ min = "1 A" }', "{}"))}


def test_an_mcb_icu_arrives_as_a_breaker_block(tmp_path):
    block = _stored(tmp_path, _block(_AC, "mcb", "icu"))
    assert isinstance(block, Breaker)
    assert block.icu.max == Quantity(Decimal(10000), Unit.A)
    assert block.icn is None


def test_a_block_without_figures_stores_no_facet(tmp_path):
    model = freeze(fransys_parts.load_path(part_root(tmp_path, _HEAD + _PROTECTION + '\n[function.block]\ntype = "rcd"\n')))
    assert not facets_of(model, BlockFacet)


@pytest.mark.parametrize(("kind", "key"), [("mcb", "breaking_capacity"), ("fuse", "icu"), ("rcd", "icu")])
def test_a_figure_key_the_type_does_not_take_is_unknown(tmp_path, kind, key):
    findings = _lint(tmp_path, _block(_AC, kind, key))
    assert [f.code for f in findings if f.severity is Severity.ERROR] == ["FIELD_UNKNOWN"]


_BAD = {
    "empty figure": "{}",
    "not a table": '"15000 A"',
    "unknown key": '{ max = "1 A", extra = "3" }',
    "bad quantity": '{ max = "15000", at = ["DC", "1 V"] }',
    "unknown unit": '{ max = "1 furlong", at = ["DC", "1 V"] }',
    "zero current": '{ max = "0 A", at = ["DC", "1 V"] }',
    "no current kind": '{ max = "1 A", at = ["1 V"] }',
    "no voltage and no min": '{ max = "1 A", at = ["DC"] }',
    "time constant on ac": '{ max = "2 A", at = ["AC", "1 V", "3 ms"] }',
    "not a current": '{ max = "2 V", at = ["DC", "1 V"] }',
}


@pytest.mark.parametrize("case", sorted(_BAD))
def test_a_malformed_figure_is_rating_value_invalid(tmp_path, case):
    findings = _lint(tmp_path, _block(_BAD[case]))
    assert findings
    assert {f.code for f in findings} <= {"RATING_VALUE_INVALID", "FIELD_TYPE"}
    assert all(f.severity is Severity.ERROR for f in findings)
