"""Decision model-0080: `[function.connector] gender` is optional; absent means not stated.

An absent gender lints clean, loads as `ConnectorFacet.gender is None` and reaches
`connector_rows` as `None`; a present gender is still checked against `Gender`.
"""

import fransys_parts
import pytest
from fransys_parts import PartLibraryError

from fransys_model.derive import connector_rows
from fransys_model.kernel import Origin, freeze
from fransys_model.vocab import (
    Gender,
    Item,
    PartBundle,
    function_templates,
    instantiate,
    internal_links,
    parts,
    port_templates,
)
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.tables import facets_of

pytestmark = pytest.mark.wp("parts")

_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_PART = """schema = 1

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
pincount = 1
"""
_ORIGIN = Origin(file="tests/test_connector_gender.py", line=1, note="model-0080 tests")


def _library(tmp_path, gender_line=""):
    (tmp_path / "library.toml").write_text(_LIBRARY)
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(_PART + gender_line)
    return tmp_path


def test_an_absent_gender_lints_clean_loads_as_none_and_reaches_the_connector_row(tmp_path):
    root = _library(tmp_path)
    assert fransys_parts.lint(root) == ()

    draft = fransys_parts.load_path(root)
    model = freeze(draft)
    (facet,) = facets_of(model, ConnectorFacet).values()
    assert facet.gender is None

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


def test_a_present_gender_still_loads_onto_the_facet(tmp_path):
    root = _library(tmp_path, 'gender = "female"\n')
    assert fransys_parts.lint(root) == ()
    (facet,) = facets_of(freeze(fransys_parts.load_path(root)), ConnectorFacet).values()
    assert facet.gender is Gender.FEMALE


def test_a_gender_that_is_not_a_member_is_refused_by_lint_and_by_load(tmp_path):
    root = _library(tmp_path, 'gender = "hermaphrodite"\n')
    assert "ENUM_VALUE" in {finding.code for finding in fransys_parts.lint(root)}
    with pytest.raises(PartLibraryError):
        fransys_parts.load_path(root)


def test_a_gender_that_is_not_a_string_is_a_type_finding(tmp_path):
    root = _library(tmp_path, "gender = 1\n")
    assert "FIELD_TYPE" in {finding.code for finding in fransys_parts.lint(root)}
