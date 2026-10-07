"""Decision parts-0016: `[function.connector] mates` lists the MPNs a connector mates with.

Data only: it loads onto `ConnectorFacet.mates` in file order; absent means `()`; a value that
is not a list of strings is a `FIELD_TYPE` finding.
"""

import fransys_parts
import pytest

from fransys_model.kernel import freeze
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


def _library(tmp_path, extra=""):
    (tmp_path / "library.toml").write_text(_LIBRARY)
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(_PART + extra)
    return tmp_path


def test_mates_load_onto_the_facet_in_file_order(tmp_path):
    root = _library(tmp_path, 'mates = ["B-2", "A-1"]\n')
    assert fransys_parts.lint(root) == ()
    (facet,) = facets_of(freeze(fransys_parts.load_path(root)), ConnectorFacet).values()
    assert facet.mates == ("B-2", "A-1")


def test_absent_mates_load_as_an_empty_tuple(tmp_path):
    root = _library(tmp_path)
    assert fransys_parts.lint(root) == ()
    (facet,) = facets_of(freeze(fransys_parts.load_path(root)), ConnectorFacet).values()
    assert facet.mates == ()


@pytest.mark.parametrize("line", ['mates = "B-2"\n', "mates = [1]\n", 'mates = ["B-2", 3]\n'])
def test_mates_that_are_not_a_list_of_strings_are_a_type_finding(tmp_path, line):
    findings = fransys_parts.lint(_library(tmp_path, line))
    assert [f.code for f in findings] == ["FIELD_TYPE"]
