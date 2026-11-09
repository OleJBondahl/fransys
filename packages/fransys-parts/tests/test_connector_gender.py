"""Decision model-0080: `[function.connector] gender` is optional; absent means not stated.

An absent gender lints clean, loads as `ConnectorFacet.gender is None` and reaches
`connector_rows` as `None`; a present gender is still checked against `Gender`.
"""

import fransys_parts
import pytest
from fransys_author.instantiate import instantiate
from fransys_parts import PartLibraryError

from fransys_model.derive import connector_rows, function_templates, internal_links, port_templates
from fransys_model.elecdef import Gender
from fransys_model.kernel import Origin, freeze
from fransys_model.vocab import Item, PartBundle, parts
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.tables import facets_of

pytestmark = pytest.mark.wp("parts")

_LIBRARY = 'schema = 2\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_PART = """schema = 2

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"

[[function]]
name = "x1"
kind = "connector"
ports = [{ name = "1", role = "generic" }]

[function.connector]
style = "s"
poles = 1
"""
_ORIGIN = Origin(file="tests/test_connector_gender.py", line=1, note="model-0080 tests")


def _library(tmp_path, gender_line="", poles="poles = 1\n"):
    (tmp_path / "library.toml").write_text(_LIBRARY)
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(_PART.replace("poles = 1\n", poles) + gender_line)
    return tmp_path


def test_an_absent_gender_lints_clean_loads_as_none_and_reaches_the_connector_row(tmp_path):
    root = _library(tmp_path)
    assert fransys_parts.lint(root) == ()

    draft = fransys_parts.load_path(root)
    model = freeze(draft)
    (facet,) = facets_of(model, ConnectorFacet).values()
    assert facet.connector.gender is None

    (part,) = parts(model).values()
    bundle = PartBundle(
        part=part,
        function_templates=tuple(function_templates(model).values()),
        port_templates=tuple(port_templates(model).values()),
        internal_links=tuple(internal_links(model).values()),
    )
    stamped = instantiate(bundle, ("j1",), tag="J1")
    draft.extend(stamped, origin=_ORIGIN)
    (item,) = (record for record in stamped if isinstance(record, Item))
    (row,) = connector_rows(freeze(draft), item.id)
    assert row.gender is None


@pytest.mark.parametrize(("word", "gender"), [("male", Gender.MALE), ("female", Gender.FEMALE), ("genderless", Gender.GENDERLESS)])
def test_a_present_gender_still_loads_onto_the_facet(tmp_path, word, gender):
    root = _library(tmp_path, f'gender = "{word}"\n')
    assert fransys_parts.lint(root) == ()
    (facet,) = facets_of(freeze(fransys_parts.load_path(root)), ConnectorFacet).values()
    assert facet.connector.gender is gender


def test_a_gender_that_is_not_a_member_is_refused_by_lint_and_by_load(tmp_path):
    root = _library(tmp_path, 'gender = "hermaphrodite"\n')
    assert "ENUM_VALUE" in {finding.code for finding in fransys_parts.lint(root)}
    with pytest.raises(PartLibraryError):
        fransys_parts.load_path(root)


def test_a_gender_that_is_not_a_string_is_a_type_finding(tmp_path):
    root = _library(tmp_path, "gender = 1\n")
    assert "FIELD_TYPE" in {finding.code for finding in fransys_parts.lint(root)}


def test_poles_below_one_is_elecdefs_refusal_turned_into_a_finding(tmp_path):
    root = _library(tmp_path, poles="poles = 0\n")
    findings = [finding for finding in fransys_parts.lint(root) if finding.code == "FIELD_TYPE"]
    assert findings
    assert "positive int" in findings[0].message
    with pytest.raises(PartLibraryError):
        fransys_parts.load_path(root)


def test_a_connector_without_poles_is_a_missing_field(tmp_path):
    root = _library(tmp_path, poles="")
    assert "FIELD_MISSING" in {finding.code for finding in fransys_parts.lint(root)}


def test_the_old_pincount_key_is_an_unknown_field_and_the_load_refuses_it(tmp_path):
    root = _library(tmp_path, poles="pincount = 3\n")
    assert "FIELD_UNKNOWN" in {finding.code for finding in fransys_parts.lint(root)}
    with pytest.raises(PartLibraryError):
        fransys_parts.load_path(root)
