"""One can-fail test and one clean twin per P8 lint code (spec P8, ROADMAP rule 4).

Every test builds a small library in `tmp_path`: a `library.toml` and, unless a test is
about `library.toml` itself, one part file under `parts/`. `_codes` reads back the set of
finding codes `lint` returned, so a test checks exactly the code (and severity) its check
owns, not incidental noise from the rest of the file.
"""

import itertools
from pathlib import Path

import fransys_parts
import pytest

from fransys_model.kernel import Severity

_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_roots = itertools.count()

# A minimal, lint-clean part file: one function, one port, no facets.
_CLEAN_PART = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"

[[function]]
name = "f1"
kind = "generic"
ports = [{ name = "1", role = "generic" }]
"""

_ONE_PORT = 'ports = [{ name = "1", role = "generic" }]'
_TWO_PORTS = 'ports = [{ name = "1", role = "generic" }, { name = "2", role = "generic" }]'
_LINK_1_2 = 'links = [{ a = "1", b = "2", kind = "conductive" }]'


def _root(tmp_path, *, library=_LIBRARY, parts=None, file_name="p.toml"):
    root = tmp_path / f"lib-{next(_roots)}"
    root.mkdir()
    (root / "library.toml").write_text(library)
    parts_dir = root / "parts"
    parts_dir.mkdir()
    if parts is None:
        parts = {file_name: _CLEAN_PART}
    for name, text in parts.items():
        (parts_dir / name).write_text(text)
    return root


def _findings(root):
    return fransys_parts.lint(root)


def _codes(root):
    return {f.code for f in _findings(root)}


def test_clean_library_lints_clean(tmp_path):
    assert _findings(_root(tmp_path)) == ()


def test_library_file_missing(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    findings = _findings(root)
    assert [f.code for f in findings] == ["LIBRARY_FILE_MISSING"]
    assert findings[0].severity is Severity.ERROR


def test_toml_invalid(tmp_path):
    root = _root(tmp_path, parts={"p.toml": "schema = 1\n[part\n"})
    findings = _findings(root)
    assert "TOML_INVALID" in _codes(root)
    assert "TOML_INVALID" not in _codes(_root(tmp_path))
    assert findings[0].message.startswith("parts/p.toml:1: ")


def test_file_unreadable(tmp_path):
    """A non-UTF-8 file is a finding, not a crash out of `lint`."""
    root = _root(tmp_path)
    (root / "parts" / "p.toml").write_bytes(b"\xb5")
    findings = _findings(root)
    assert [f.code for f in findings] == ["FILE_UNREADABLE"]
    assert findings[0].severity is Severity.ERROR
    assert "FILE_UNREADABLE" not in _codes(_root(tmp_path))
    assert findings[0].message.startswith("parts/p.toml:1: ")


def test_schema_unsupported_on_library(tmp_path):
    root = _root(tmp_path, library='schema = 2\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n')
    assert "SCHEMA_UNSUPPORTED" in _codes(root)
    assert "SCHEMA_UNSUPPORTED" not in _codes(_root(tmp_path))


def test_schema_unsupported_on_part_file(tmp_path):
    broken = _CLEAN_PART.replace("schema = 1", "schema = 2", 1)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "SCHEMA_UNSUPPORTED" in _codes(root)


def test_schema_mixed(tmp_path):
    broken = _CLEAN_PART.replace("schema = 1", "schema = 2", 1)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "SCHEMA_MIXED" in _codes(root)
    assert "SCHEMA_MIXED" not in _codes(_root(tmp_path))


def test_schema_missing_key(tmp_path):
    broken = _CLEAN_PART.replace("schema = 1\n", "", 1)
    root = _root(tmp_path, parts={"p.toml": broken})
    (finding,) = [f for f in _findings(root) if f.code == "FIELD_MISSING"]
    assert finding.message == "parts/p.toml:1: part file is missing 'schema'"


def test_schema_not_an_int(tmp_path):
    broken = _CLEAN_PART.replace("schema = 1", 'schema = "1"', 1)
    root = _root(tmp_path, parts={"p.toml": broken})
    (finding,) = [f for f in _findings(root) if f.code == "FIELD_TYPE"]
    assert finding.message == "parts/p.toml:1: schema must be int, not str"


def test_schema_unsupported_and_mixed_name_the_part_files_own_path_and_line_one(tmp_path):
    broken = _CLEAN_PART.replace("schema = 1", "schema = 2", 1)
    root = _root(tmp_path, parts={"p.toml": broken})
    findings = _findings(root)
    (unsupported,) = [f for f in findings if f.code == "SCHEMA_UNSUPPORTED"]
    (mixed,) = [f for f in findings if f.code == "SCHEMA_MIXED"]
    assert unsupported.message == "parts/p.toml:1: schema 2 is not supported (supported: 1)"
    assert mixed.message == "parts/p.toml:1: schema 2 differs from library.toml's schema 1"


def test_table_unknown(tmp_path):
    broken = _CLEAN_PART + "\n[bogus]\nx = 1\n"
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "TABLE_UNKNOWN" in _codes(root)
    assert "TABLE_UNKNOWN" not in _codes(_root(tmp_path))


def test_table_unknown_array_reports_its_own_header_line(tmp_path):
    broken = _CLEAN_PART + '\n[[bogus]]\nx = "1"\n'
    root = _root(tmp_path, parts={"p.toml": broken})
    (finding,) = [f for f in _findings(root) if f.code == "TABLE_UNKNOWN"]
    line = int(finding.message.split(":")[1])
    assert broken.splitlines()[line - 1] == "[[bogus]]"


def test_field_unknown(tmp_path):
    broken = _CLEAN_PART.replace('class_code = "X"', 'class_code = "X"\nbogus_field = "y"')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FIELD_UNKNOWN" in _codes(root)
    assert "FIELD_UNKNOWN" not in _codes(_root(tmp_path))


def test_field_missing(tmp_path):
    broken = _CLEAN_PART.replace('class_code = "X"\n', "")
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FIELD_MISSING" in _codes(root)
    assert "FIELD_MISSING" not in _codes(_root(tmp_path))


def test_field_type(tmp_path):
    broken = _CLEAN_PART.replace('class_code = "X"', "class_code = 1")
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FIELD_TYPE" in _codes(root)
    assert "FIELD_TYPE" not in _codes(_root(tmp_path))


def test_float_forbidden(tmp_path):
    broken = _CLEAN_PART.replace('mpn = "X-1"', "mpn = 1.5")
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FLOAT_FORBIDDEN" in _codes(root)
    assert "FLOAT_FORBIDDEN" not in _codes(_root(tmp_path))


def test_float_forbidden_under_an_unknown_field_is_still_reported(tmp_path):
    """FLOAT_FORBIDDEN fires anywhere in the file, an unknown field included (both fire)."""
    broken = _CLEAN_PART.replace('class_code = "X"', 'class_code = "X"\nbogus_field = 1.5')
    codes = _codes(_root(tmp_path, parts={"p.toml": broken}))
    assert "FIELD_UNKNOWN" in codes
    assert "FLOAT_FORBIDDEN" in codes


def test_float_forbidden_under_an_unknown_table_is_still_reported(tmp_path):
    """FLOAT_FORBIDDEN fires anywhere in the file, an unknown table included (both fire)."""
    broken = _CLEAN_PART + "\n[bogus]\nx = 1.5\n"
    codes = _codes(_root(tmp_path, parts={"p.toml": broken}))
    assert "TABLE_UNKNOWN" in codes
    assert "FLOAT_FORBIDDEN" in codes
    assert "FLOAT_FORBIDDEN" in codes


def test_float_forbidden_inside_a_list_element(tmp_path):
    """A bare float used as one element of a list value is walked and reported too."""
    cable_product = (
        '[cable_product]\ncore_count = 1\ncore_colours = [1.5]\ngauge_mm2 = "1.5"\nshielded = false'
    )
    part = _CLEAN_PART.replace('category = "generic"', 'category = "cable"').replace(
        'class_code = "X"', f'class_code = "W"\n\n{cable_product}'
    )
    root = _root(tmp_path, parts={"p.toml": part})
    assert "FLOAT_FORBIDDEN" in _codes(root)


def test_float_forbidden_line_for_a_value_nested_under_a_known_table(tmp_path):
    """FLOAT_FORBIDDEN nested two levels deep inside a known table (`[function.connector]`)
    carries that table's own header line, not the line-1 fallback."""
    connector = (
        '\n[function.connector]\nstyle = "s"\npincount = 1\ngender = "male"\nextra_float = 1.5\n'
    )
    broken = _CLEAN_PART.replace('kind = "generic"', 'kind = "connector"') + connector
    root = _root(tmp_path, parts={"p.toml": broken})
    lines = broken.splitlines()
    connector_header_line = lines.index("[function.connector]") + 1
    (finding,) = [f for f in _findings(root) if f.code == "FLOAT_FORBIDDEN"]
    assert finding.message == (
        f"parts/p.toml:{connector_header_line}: a bare TOML float; write it as a quoted string"
    )


def test_multiline_string(tmp_path):
    """The check is made on the parsed value, so a genuine embedded line break is needed."""
    broken = _CLEAN_PART.replace('description = "d"', 'description = """line one\nline two"""')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "MULTILINE_STRING" in _codes(root)
    assert "MULTILINE_STRING" not in _codes(_root(tmp_path))


def test_multiline_string_syntax_with_no_line_break_is_clean(tmp_path):
    r"""`\"""d\"""` is valid TOML multi-line-string *syntax* but holds no line break."""
    clean = _CLEAN_PART.replace('description = "d"', 'description = """d"""')
    assert "MULTILINE_STRING" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_multiline_string_comment_is_clean(tmp_path):
    """A comment holding triple quotes is not a string value: no misfire on raw text."""
    clean = _CLEAN_PART.replace('description = "d"', 'description = "d"  # see """x"""')
    assert "MULTILINE_STRING" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_multiline_string_literal_quotes_in_a_value_is_clean(tmp_path):
    """A single-line string whose content happens to include `'''` has no line break."""
    clean = _CLEAN_PART.replace('description = "d"', "description = \"it has ''' inside\"")
    assert "MULTILINE_STRING" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_enum_value(tmp_path):
    broken = _CLEAN_PART.replace('category = "generic"', 'category = "not-a-category"')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "ENUM_VALUE" in _codes(root)
    assert "ENUM_VALUE" not in _codes(_root(tmp_path))


def test_part_duplicate(tmp_path):
    root = _root(tmp_path, parts={"a.toml": _CLEAN_PART, "b.toml": _CLEAN_PART})
    assert "PART_DUPLICATE" in _codes(root)
    other = _CLEAN_PART.replace('mpn = "X-1"', 'mpn = "X-2"')
    clean = _root(tmp_path, parts={"a.toml": _CLEAN_PART, "b.toml": other})
    assert "PART_DUPLICATE" not in _codes(clean)


def test_function_name_duplicate(tmp_path):
    port_2 = _ONE_PORT.replace('"1"', '"2"')
    second = f'\n[[function]]\nname = "f1"\nkind = "generic"\n{port_2}\n'
    broken = _CLEAN_PART + second
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FUNCTION_NAME_DUPLICATE" in _codes(root)
    assert "FUNCTION_NAME_DUPLICATE" not in _codes(_root(tmp_path))


def test_port_name_duplicate(tmp_path):
    two_of_one = 'ports = [{ name = "1", role = "generic" }, { name = "1", role = "generic" }]'
    broken = _CLEAN_PART.replace(_ONE_PORT, two_of_one)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "PORT_NAME_DUPLICATE" in _codes(root)
    assert "PORT_NAME_DUPLICATE" not in _codes(_root(tmp_path))


def test_function_without_ports(tmp_path):
    broken = _CLEAN_PART.replace(_ONE_PORT, "ports = []")
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FUNCTION_WITHOUT_PORTS" in _codes(root)
    assert "FUNCTION_WITHOUT_PORTS" not in _codes(_root(tmp_path))


def test_function_without_ports_reports_the_second_functions_own_line(tmp_path):
    """FUNCTION_WITHOUT_PORTS must carry the line of the function it's actually on, not the
    first function's line (the per-function `line` lookup, not a default or a hardcoded one)."""
    second = '\n[[function]]\nname = "f2"\nkind = "generic"\nports = []\n'
    part = _CLEAN_PART + second
    root = _root(tmp_path, parts={"p.toml": part})
    lines = part.splitlines()
    first_header = lines.index("[[function]]")
    second_header_line = lines.index("[[function]]", first_header + 1) + 1
    (finding,) = [f for f in _findings(root) if f.code == "FUNCTION_WITHOUT_PORTS"]
    assert finding.message.startswith(f"parts/p.toml:{second_header_line}:")


def test_port_name_duplicate_reports_the_second_functions_own_line(tmp_path):
    """PORT_NAME_DUPLICATE must carry the line of the function it's actually on, not the
    first function's line."""
    two_of_one = 'ports = [{ name = "1", role = "generic" }, { name = "1", role = "generic" }]'
    second = f'\n[[function]]\nname = "f2"\nkind = "generic"\n{two_of_one}\n'
    part = _CLEAN_PART + second
    root = _root(tmp_path, parts={"p.toml": part})
    lines = part.splitlines()
    first_header = lines.index("[[function]]")
    second_header_line = lines.index("[[function]]", first_header + 1) + 1
    (finding,) = [f for f in _findings(root) if f.code == "PORT_NAME_DUPLICATE"]
    assert finding.message.startswith(f"parts/p.toml:{second_header_line}:")


def test_link_port_unknown(tmp_path):
    broken = _CLEAN_PART.replace(_ONE_PORT, _ONE_PORT + "\n" + _LINK_1_2)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "LINK_PORT_UNKNOWN" in _codes(root)
    clean = _CLEAN_PART.replace(_ONE_PORT, _TWO_PORTS + "\n" + _LINK_1_2)
    assert "LINK_PORT_UNKNOWN" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_link_self(tmp_path):
    link_self = 'links = [{ a = "1", b = "1", kind = "conductive" }]'
    broken = _CLEAN_PART.replace(_ONE_PORT, _ONE_PORT + "\n" + link_self)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "LINK_SELF" in _codes(root)
    assert "LINK_SELF" not in _codes(_root(tmp_path))


def test_links_with_no_ports_key_reports_link_port_unknown_not_a_crash(tmp_path):
    """A function with `links` but no `ports` key at all must not crash `_check_links`."""
    part = _PART_HEAD + '[[function]]\nname = "f1"\nkind = "generic"\n' + _LINK_1_2 + "\n"
    root = _root(tmp_path, parts={"p.toml": part})
    findings = _findings(root)
    assert "LINK_PORT_UNKNOWN" in {f.code for f in findings}


def test_link_self_reports_the_owning_functions_own_line(tmp_path):
    """LINK_SELF must carry the line of the function that owns the bad link, not another one's."""
    link_self = 'links = [{ a = "1", b = "1", kind = "conductive" }]'
    second = f'\n[[function]]\nname = "f2"\nkind = "generic"\n{_ONE_PORT}\n{link_self}\n'
    part = _CLEAN_PART + second
    root = _root(tmp_path, parts={"p.toml": part})
    lines = part.splitlines()
    first_header = lines.index("[[function]]")
    second_header_line = lines.index("[[function]]", first_header + 1) + 1
    (finding,) = [f for f in _findings(root) if f.code == "LINK_SELF"]
    assert finding.message.startswith(f"parts/p.toml:{second_header_line}:")


def test_link_duplicate(tmp_path):
    a_to_b = '{ a = "1", b = "2", kind = "conductive" }'
    b_to_a = '{ a = "2", b = "1", kind = "conductive" }'
    two_links = f"links = [{a_to_b}, {b_to_a}]"
    broken = _CLEAN_PART.replace(_ONE_PORT, _TWO_PORTS + "\n" + two_links)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "LINK_DUPLICATE" in _codes(root)
    clean = _CLEAN_PART.replace(_ONE_PORT, _TWO_PORTS + "\n" + _LINK_1_2)
    assert "LINK_DUPLICATE" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_symbol_slug(tmp_path):
    broken = _CLEAN_PART.replace('kind = "generic"', 'kind = "generic"\nsymbol = "Not_A_Slug"')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "SYMBOL_SLUG" in _codes(root)
    clean = _CLEAN_PART.replace('kind = "generic"', 'kind = "generic"\nsymbol = "a-slug"')
    assert "SYMBOL_SLUG" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_symbol_port_without_symbol(tmp_path):
    with_symbol_port = 'ports = [{ name = "1", role = "generic", symbol_port = "in" }]'
    broken = _CLEAN_PART.replace(_ONE_PORT, with_symbol_port)
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "SYMBOL_PORT_WITHOUT_SYMBOL" in _codes(root)
    clean = _CLEAN_PART.replace('kind = "generic"', 'kind = "generic"\nsymbol = "a-slug"').replace(
        _ONE_PORT, with_symbol_port
    )
    assert "SYMBOL_PORT_WITHOUT_SYMBOL" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_class_letter_field_removed(tmp_path):
    """C1: a part file that still uses the old `class_letter` field fails to load."""
    broken = _CLEAN_PART.replace('class_code = "X"', 'class_letter = "K"')
    root = _root(tmp_path, parts={"p.toml": broken})
    codes = _codes(root)
    assert "FIELD_UNKNOWN" in codes
    assert "FIELD_MISSING" in codes
    with pytest.raises(fransys_parts.PartLibraryError):
        fransys_parts.load_path(root)


def test_class_code(tmp_path):
    broken = _CLEAN_PART.replace('class_code = "X"', 'class_code = "Xx"')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "CLASS_CODE" in _codes(root)
    assert "CLASS_CODE" not in _codes(_root(tmp_path))
    part_line = next(
        i for i, line in enumerate(broken.splitlines(), start=1) if line.strip() == "[part]"
    )
    findings = [f for f in _findings(root) if f.code == "CLASS_CODE"]
    assert findings[0].message.startswith(f"parts/p.toml:{part_line}:")


@pytest.mark.parametrize(
    ("code", "expected_message_fragment"),
    [
        ("A", "class_code 'A' is forbidden by IEC 81346-2:2019"),
        ("I", "class_code 'I' is forbidden by IEC 81346-2:2019"),
        ("O", "class_code 'O' is forbidden by IEC 81346-2:2019"),
        ("V", "class_code 'V' is reserved by IEC 81346-2:2019"),
        ("QAAA", "class_code 'QAAA' must be 1 to 3 uppercase letters"),
        ("q", "class_code 'q' must be 1 to 3 uppercase letters"),
    ],
    ids=["A", "I", "O", "V", "QAAA", "q"],
)
def test_class_code_iec_81346_2_2019(tmp_path, code, expected_message_fragment):
    broken = _CLEAN_PART.replace('class_code = "X"', f'class_code = "{code}"')
    root = _root(tmp_path, parts={"p.toml": broken})
    findings = [f for f in _findings(root) if f.code == "CLASS_CODE"]
    assert len(findings) == 1
    assert expected_message_fragment in findings[0].message


@pytest.mark.parametrize("code", ["Q", "QA", "J", "U"])
def test_class_code_iec_81346_2_2019_passes(tmp_path, code):
    clean = _CLEAN_PART.replace('class_code = "X"', f'class_code = "{code}"')
    root = _root(tmp_path, parts={"p.toml": clean})
    assert "CLASS_CODE" not in _codes(root)


_CABLE_PRODUCT = (
    "[cable_product]\n"
    'core_count = 3\ncore_colours = ["BN", "BK"]\ngauge_mm2 = "1.5"\nshielded = false'
)


def test_cable_core_count(tmp_path):
    part = _CLEAN_PART.replace('category = "generic"', 'category = "cable"').replace(
        'class_code = "X"', f'class_code = "W"\n\n{_CABLE_PRODUCT}'
    )
    root = _root(tmp_path, parts={"p.toml": part})
    assert "CABLE_CORE_COUNT" in _codes(root)
    cable_product_line = next(
        i for i, line in enumerate(part.splitlines(), start=1) if line.strip() == "[cable_product]"
    )
    findings = [f for f in _findings(root) if f.code == "CABLE_CORE_COUNT"]
    assert findings[0].message.startswith(f"parts/p.toml:{cable_product_line}:")
    clean = part.replace("core_count = 3", "core_count = 2")
    assert "CABLE_CORE_COUNT" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_cable_without_product_missing(tmp_path):
    broken = _CLEAN_PART.replace('category = "generic"', 'category = "cable"')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "CABLE_WITHOUT_PRODUCT" in _codes(root)
    findings = [f for f in _findings(root) if f.code == "CABLE_WITHOUT_PRODUCT"]
    part_line = next(
        i for i, line in enumerate(broken.splitlines(), start=1) if line.strip() == "[part]"
    )
    assert findings[0].message.startswith(f"parts/p.toml:{part_line}:")


_CABLE_PRODUCT_ONE_CORE = (
    '[cable_product]\ncore_count = 1\ncore_colours = ["BN"]\ngauge_mm2 = "1.5"\nshielded = false'
)


def test_cable_without_product_on_wrong_category(tmp_path):
    broken = _CLEAN_PART.replace(
        'class_code = "X"', f'class_code = "X"\n\n{_CABLE_PRODUCT_ONE_CORE}'
    )
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "CABLE_WITHOUT_PRODUCT" in _codes(root)
    clean = broken.replace('category = "generic"', 'category = "cable"').replace(
        'class_code = "X"\n', 'class_code = "W"\n'
    )
    assert "CABLE_WITHOUT_PRODUCT" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_cable_core_colours_entry_not_a_string(tmp_path):
    """`core_colours` is the only field with `elem_type=str`; a non-string entry is FIELD_TYPE."""
    bad_product = (
        "[cable_product]\n"
        'core_count = 2\ncore_colours = ["red", 1]\ngauge_mm2 = "1.5"\nshielded = false'
    )
    part = _CLEAN_PART.replace('category = "generic"', 'category = "cable"').replace(
        'class_code = "X"', f'class_code = "W"\n\n{bad_product}'
    )
    root = _root(tmp_path, parts={"p.toml": part})
    (finding,) = [f for f in _findings(root) if f.code == "FIELD_TYPE"]
    assert "cable_product.core_colours entries must all be str" in finding.message


def test_facet_kind_mismatch_connector(tmp_path):
    broken = _CLEAN_PART + '\n[function.connector]\nstyle = "s"\npincount = 4\ngender = "male"\n'
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FACET_KIND_MISMATCH" in _codes(root)
    clean = broken.replace('kind = "generic"', 'kind = "connector"')
    assert "FACET_KIND_MISMATCH" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_facet_kind_mismatch_plc_channel(tmp_path):
    broken = _CLEAN_PART + '\n[function.plc_channel]\nsignal = "di"\nchannel = 1\n'
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "FACET_KIND_MISMATCH" in _codes(root)
    clean = broken.replace('kind = "generic"', 'kind = "plc_channel"')
    assert "FACET_KIND_MISMATCH" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_pincount(tmp_path):
    broken = (
        _CLEAN_PART.replace('kind = "generic"', 'kind = "connector"')
        + '\n[function.connector]\nstyle = "s"\npincount = 0\ngender = "male"\n'
    )
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "PINCOUNT" in _codes(root)
    clean = broken.replace("pincount = 0", "pincount = 1")
    assert "PINCOUNT" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_pincount_and_facet_kind_mismatch_report_the_second_functions_own_line(tmp_path):
    """PINCOUNT and FACET_KIND_MISMATCH must carry the line of the function whose
    `[function.connector]` facet they're actually on, not the first function's line."""
    second = (
        '\n[[function]]\nname = "f2"\nkind = "generic"\n'
        + _ONE_PORT
        + '\n\n[function.connector]\nstyle = "s"\npincount = 0\ngender = "male"\n'
    )
    part = _CLEAN_PART + second
    root = _root(tmp_path, parts={"p.toml": part})
    lines = part.splitlines()
    first_header = lines.index("[[function]]")
    second_header_line = lines.index("[[function]]", first_header + 1) + 1
    findings = _findings(root)
    (pincount,) = [f for f in findings if f.code == "PINCOUNT"]
    (mismatch,) = [f for f in findings if f.code == "FACET_KIND_MISMATCH"]
    assert pincount.message.startswith(f"parts/p.toml:{second_header_line}:")
    assert mismatch.message.startswith(f"parts/p.toml:{second_header_line}:")


_PART_HEAD = _CLEAN_PART[: _CLEAN_PART.index("[[function]]")]


def _function(name, kind, marking=None):
    """One `[[function]]` with the port `1`; a connector gets its facet, `marking` if given."""
    text = f'[[function]]\nname = "{name}"\nkind = "{kind}"\n{_ONE_PORT}\n'
    if kind == "connector":
        text += '\n[function.connector]\nstyle = "s"\npincount = 1\ngender = "male"\n'
        if marking is not None:
            text += f"marking = {marking}\n"
    return text + "\n"


def _part_of(*functions):
    return {"p.toml": _PART_HEAD + "".join(functions)}


def test_port_name_shared_between_two_functions(tmp_path):
    root = _root(tmp_path, parts=_part_of(_function("coil", "coil"), _function("k", "contact_no")))
    (finding,) = [f for f in _findings(root) if f.code == "PORT_NAME_SHARED"]
    assert finding.severity is Severity.ERROR
    assert "'1'" in finding.message
    assert "'coil'" in finding.message
    assert "'k'" in finding.message
    other = _function("k", "contact_no").replace('name = "1"', 'name = "2"')
    clean = _root(tmp_path, parts=_part_of(_function("coil", "coil"), other))
    assert "PORT_NAME_SHARED" not in _codes(clean)


def test_port_name_shared_reported_once_per_name_and_later_function(tmp_path):
    root = _root(
        tmp_path,
        parts=_part_of(_function("a", "coil"), _function("b", "coil"), _function("c", "coil")),
    )
    shared = [f for f in _findings(root) if f.code == "PORT_NAME_SHARED"]
    assert len(shared) == 2


def test_a_port_name_that_is_not_a_string_is_a_field_type_finding_not_a_crash(tmp_path):
    """The shared-name check reads names before the field check reports a bad one."""
    bad = _function("b", "coil").replace('name = "1"', 'name = ["1"]')
    root = _root(tmp_path, parts=_part_of(_function("a", "coil"), bad))
    codes = _codes(root)
    assert "FIELD_TYPE" in codes
    assert "PORT_NAME_SHARED" not in codes


def test_port_name_shared_allows_two_connector_functions(tmp_path):
    root = _root(
        tmp_path, parts=_part_of(_function("x1", "connector"), _function("x2", "connector"))
    )
    codes = _codes(root)
    assert "PORT_NAME_SHARED" not in codes
    assert "CONNECTOR_MARKING_REUSED" not in codes


def test_an_unlabelled_connector_may_not_share_a_port_name_with_another_connector(tmp_path):
    """`marking = ""` prints no label, so its pins print under the item and would read as the
    other connector's: the ruling that keeps a housing's shell out of the sub-part form."""
    shell = _function("shell", "connector", '""')
    root = _root(tmp_path, parts=_part_of(_function("p1", "connector"), shell))
    assert "PORT_NAME_SHARED" in _codes(root)
    assert "PORT_NAME_SHARED" in _codes(
        _root(tmp_path, parts=_part_of(shell, _function("p1", "connector")))
    )
    distinct = shell.replace('name = "1"', 'name = "PE"')
    assert "PORT_NAME_SHARED" not in _codes(
        _root(tmp_path, parts=_part_of(_function("p1", "connector"), distinct))
    )


def test_two_unlabelled_connectors_are_no_marking_reuse(tmp_path):
    """No label is not one label: the empty marking is never a reused label."""
    one, two = (_function(name, "connector", '""') for name in ("a", "b"))
    two = two.replace('name = "1"', 'name = "2"')
    codes = _codes(_root(tmp_path, parts=_part_of(one, two)))
    assert "CONNECTOR_MARKING_REUSED" not in codes
    assert "PORT_NAME_SHARED" not in codes


@pytest.mark.parametrize("connector_first", [True, False])
def test_port_name_shared_connector_with_non_connector(tmp_path, connector_first):
    pair = [_function("x1", "connector"), _function("k", "contact_no")]
    root = _root(tmp_path, parts=_part_of(*(pair if connector_first else pair[::-1])))
    assert "PORT_NAME_SHARED" in _codes(root)


def _shared(root):
    return [f for f in _findings(root) if f.code == "PORT_NAME_SHARED"]


def test_the_demo_clamps_and_sockets_part_lints_clean():
    """CASE 1: a clamp strip beside labelled sockets `X1`, `X2`, `X4`, all with a pin `1`, print
    `-A1:1`, `-A1-X1:1`, `-A1-X2:1`, `-A1-X4:1`: one text each, so no finding."""
    import demo_parts

    root = Path(demo_parts.__file__).parent
    assert (root / "parts" / "io-clamps-and-sockets.toml").is_file()
    # MUTATION: `_check_port_names_shared` `other == segment` -> `not (other and segment)` (the
    # old "clash unless both labelled": the clamp strip shares `1` with a socket)
    assert [f for f in _findings(root) if "io-clamps-and-sockets.toml" in f.message] == []


def test_one_labelled_connector_and_a_group_sharing_a_port_name_print_one_text(tmp_path):
    """A lone label prints no segment (`-J1:1`): both functions print `<item>:1`."""
    functions = (_function("x1", "connector"), _function("clamp", "load"))
    root = _root(tmp_path, parts=_part_of(*functions))
    (finding,) = _shared(root)
    assert "'<item>:1'" in finding.message
    assert "'x1'" in finding.message
    assert "'clamp'" in finding.message


def test_two_unlabelled_groups_sharing_a_port_name_name_the_printed_text(tmp_path):
    root = _root(tmp_path, parts=_part_of(_function("a", "coil"), _function("b", "load")))
    (finding,) = _shared(root)
    assert "'<item>:1'" in finding.message


def test_a_labelled_connector_and_a_shell_without_a_marking_print_one_text(tmp_path):
    shell = _function("shell", "connector", '""')
    (finding,) = _shared(_root(tmp_path, parts=_part_of(_function("x1", "connector"), shell)))
    assert "'<item>:1'" in finding.message


def test_three_labelled_connectors_sharing_a_port_name_are_fine(tmp_path):
    functions = (_function(name, "connector") for name in ("x1", "x2", "x4"))
    assert _shared(_root(tmp_path, parts=_part_of(*functions))) == []


def test_an_unlabelled_group_may_share_a_port_name_when_two_connectors_are_labelled(tmp_path):
    """Two labels: `-x1`, `-x2` and the group's `""` are three different segments."""
    functions = (
        _function("x1", "connector"),
        _function("x2", "connector"),
        _function("clamps", "load"),
    )
    # MUTATION: `_check_port_names_shared` `segment = state.segments[index]` -> `segment = ""`
    # (the lint ignores `connector_segments`: every function prints the same segment)
    assert _shared(_root(tmp_path, parts=_part_of(*functions))) == []


def test_connector_marking_reused_by_explicit_marking(tmp_path):
    functions = (_function("a", "connector", '"X1"'), _function("b", "connector", '"X1"'))
    (finding,) = [
        f
        for f in _findings(_root(tmp_path, parts=_part_of(*functions)))
        if f.code == "CONNECTOR_MARKING_REUSED"
    ]
    assert finding.severity is Severity.ERROR
    assert "'X1'" in finding.message
    assert "'a'" in finding.message
    assert "'b'" in finding.message
    distinct = (_function("a", "connector", '"X1"'), _function("b", "connector", '"X2"'))
    assert "CONNECTOR_MARKING_REUSED" not in _codes(_root(tmp_path, parts=_part_of(*distinct)))


def test_connector_marking_reused_label_falls_back_to_the_name(tmp_path):
    functions = (_function("a", "connector", '"x2"'), _function("x2", "connector"))
    root = _root(tmp_path, parts=_part_of(*functions))
    assert "CONNECTOR_MARKING_REUSED" in _codes(root)
    other_way = (_function("x2", "connector"), _function("a", "connector", '"x2"'))
    assert "CONNECTOR_MARKING_REUSED" in _codes(_root(tmp_path, parts=_part_of(*other_way)))


def test_connector_marking_reused_skips_a_bad_typed_marking(tmp_path):
    functions = (_function("a", "connector", "3"), _function("b", "connector", "3"))
    codes = _codes(_root(tmp_path, parts=_part_of(*functions)))
    assert "FIELD_TYPE" in codes
    assert "CONNECTOR_MARKING_REUSED" not in codes


def test_connector_marking_is_a_known_string_field(tmp_path):
    clean = _root(tmp_path, parts=_part_of(_function("x1", "connector", '"X1"')))
    assert not {"FIELD_UNKNOWN", "FIELD_TYPE"} & _codes(clean)
    bad = _root(tmp_path, parts=_part_of(_function("x1", "connector", "3")))
    assert "FIELD_TYPE" in _codes(bad)


def test_a_connector_with_a_non_str_name_is_field_type_once_not_a_crash(tmp_path):
    """`_connector_label`'s `type(name) is not str` guard must return `None` rather than let a
    non-str `name` reach `entry.get(...)`/`connector_label(...)`; a crash here would not surface
    as FIELD_TYPE but as an uncaught exception from `_findings` itself. An unhashable value (a
    table, not an int) is required to actually kill a removed guard: `connector_label`'s `name or
    None` and an f-string both tolerate a truthy scalar with no crash, but `_check_connector_
    marking_reused` uses the label as a dict key."""
    bad = _function("x1", "connector").replace('name = "x1"', "name = {a = 1}")
    root = _root(tmp_path, parts=_part_of(bad))
    findings = _findings(root)  # would raise if _connector_label crashed
    assert len([f for f in findings if f.code == "FIELD_TYPE"]) == 1


def test_a_non_dict_connector_facet_is_field_type_once_not_a_crash(tmp_path):
    """`_connector_label`'s `type(connector) is dict` guard must treat a non-table `connector`
    as having no marking, not call `.get` on it. FIELD_TYPE comes from `_fields.check_fields`'s
    own `function.connector must be a table` branch, not from `_connector_label`."""
    text = (
        '[[function]]\nname = "x1"\nkind = "connector"\n'
        + _ONE_PORT
        + '\nconnector = "not-a-table"\n\n'
    )
    root = _root(tmp_path, parts=_part_of(text))
    findings = _findings(root)  # would raise if _connector_label crashed
    assert len([f for f in findings if f.code == "FIELD_TYPE"]) == 1
    codes = _codes(root)
    assert "FACET_KIND_MISMATCH" not in codes
    assert "PINCOUNT" not in codes


def test_a_non_str_marking_inside_an_otherwise_valid_connector_is_field_type_once(tmp_path):
    """`_connector_label`'s `type(marking) is not str` guard must return `None` rather than pass
    a non-str `marking` into `connector_label`. An unhashable value (a list, not an int) is
    required to actually kill a removed guard, the same reason the name guard's test above uses a
    table: `connector_label`'s `marking or None` tolerates a truthy scalar, but
    `_check_connector_marking_reused` uses the label as a dict key."""
    root = _root(tmp_path, parts=_part_of(_function("x1", "connector", '["x"]')))
    findings = _findings(root)  # would raise if _connector_label crashed
    assert len([f for f in findings if f.code == "FIELD_TYPE"]) == 1
    assert "CONNECTOR_MARKING_REUSED" not in _codes(root)


def test_plc_channel_duplicate(tmp_path):
    one = (
        _CLEAN_PART.replace('kind = "generic"', 'kind = "plc_channel"')
        + '\n[function.plc_channel]\nsignal = "di"\nchannel = 1\n'
    )
    two = (
        f'\n[[function]]\nname = "f2"\nkind = "plc_channel"\n{_ONE_PORT}\n'
        '\n[function.plc_channel]\nsignal = "di"\nchannel = 1\n'
    )
    root = _root(tmp_path, parts={"p.toml": one + two})
    assert "PLC_CHANNEL_DUPLICATE" in _codes(root)
    two_clean = two.replace("channel = 1", "channel = 2")
    assert "PLC_CHANNEL_DUPLICATE" not in _codes(_root(tmp_path, parts={"p.toml": one + two_clean}))


def test_plc_channel_duplicate_reports_the_duplicating_functions_own_line(tmp_path):
    """PLC_CHANNEL_DUPLICATE must carry the line of the function that repeats the
    channel/signal pair, not the first function's line."""
    one = (
        _CLEAN_PART.replace('kind = "generic"', 'kind = "plc_channel"')
        + '\n[function.plc_channel]\nsignal = "di"\nchannel = 1\n'
    )
    two = (
        f'\n[[function]]\nname = "f2"\nkind = "plc_channel"\n{_ONE_PORT}\n'
        '\n[function.plc_channel]\nsignal = "di"\nchannel = 1\n'
    )
    part = one + two
    root = _root(tmp_path, parts={"p.toml": part})
    lines = part.splitlines()
    first_header = lines.index("[[function]]")
    second_header_line = lines.index("[[function]]", first_header + 1) + 1
    (finding,) = [f for f in _findings(root) if f.code == "PLC_CHANNEL_DUPLICATE"]
    assert finding.message.startswith(f"parts/p.toml:{second_header_line}:")


def _changeover(
    kind="contact_co", roles=("common", "break", "make"), names=("11", "12", "14"), links=None
):
    """One three-port function `k`; the default links join port 1 to ports 2 and 3, `switched`."""
    ports = ", ".join(
        f'{{ name = "{n}", role = "{r}" }}' for n, r in zip(names, roles, strict=True)
    )
    if links is None:
        links = [(names[0], names[1]), (names[0], names[2])]
    body = ", ".join(f'{{ a = "{a}", b = "{b}", kind = "switched" }}' for a, b in links)
    return f'[[function]]\nname = "k"\nkind = "{kind}"\nports = [{ports}]\nlinks = [{body}]\n\n'


def _changeover_codes(tmp_path, **kwargs):
    return _codes(_root(tmp_path, parts=_part_of(_changeover(**kwargs))))


def test_changeover_role(tmp_path):
    broken = _root(tmp_path, parts=_part_of(_changeover(roles=("common", "break", "generic"))))
    (finding,) = [f for f in _findings(broken) if f.code == "CHANGEOVER_ROLE"]
    assert finding.severity is Severity.ERROR
    assert "'14'" in finding.message
    assert "CHANGEOVER_ROLE" not in _changeover_codes(tmp_path)


def test_changeover_role_names_are_free(tmp_path):
    for names in (("COM", "NC", "NO"), ("1COM", "1NC", "1NO"), ("I", "II", "III")):
        assert _changeover_codes(tmp_path, names=names).isdisjoint(
            {"CHANGEOVER_ROLE", "CHANGEOVER_LINK"}
        )


@pytest.mark.parametrize(
    ("roles", "link"),
    [
        (("common", "break", "break"), ("12", "14")),
        (("common", "common", "make"), ("11", "12")),
        (("common", "break", "generic"), ("11", "14")),
    ],
    ids=["break-break", "common-common", "common-generic"],
)
def test_changeover_link(tmp_path, roles, link):
    """Break to break, common to common and common to a non-throw role are not a changeover."""
    root = _root(tmp_path, parts=_part_of(_changeover(roles=roles, links=[link])))
    (finding,) = [f for f in _findings(root) if f.code == "CHANGEOVER_LINK"]
    assert finding.severity is Severity.ERROR
    assert f"({link[0]!r}, {link[1]!r})" in finding.message
    assert "CHANGEOVER_LINK" not in _changeover_codes(tmp_path)


@pytest.mark.parametrize("swapped", [False, True])
def test_changeover_link_accepts_common_to_break_and_make_in_either_order(tmp_path, swapped):
    links = [("12", "11"), ("14", "11")] if swapped else [("11", "12"), ("11", "14")]
    codes = _changeover_codes(tmp_path, links=links)
    assert codes.isdisjoint({"CHANGEOVER_ROLE", "CHANGEOVER_LINK"})


def test_changeover_link_skips_a_conductive_link_and_a_bad_link(tmp_path):
    """Only `switched` links are checked; an unknown port and a self link have their own codes."""
    broken = _changeover(roles=("break", "break", "make"), links=[("11", "99"), ("12", "12")])
    codes = _codes(_root(tmp_path, parts=_part_of(broken)))
    assert {"LINK_PORT_UNKNOWN", "LINK_SELF"} <= codes
    assert "CHANGEOVER_LINK" not in codes
    conductive_break = _changeover(roles=("break", "break", "make"), links=[]).replace(
        "links = []", 'links = [{ a = "11", b = "12", kind = "conductive" }]'
    )
    assert "CHANGEOVER_LINK" not in _codes(_root(tmp_path, parts=_part_of(conductive_break)))


def test_throw_roles_on_another_kind_trigger_neither_changeover_code(tmp_path):
    """Only a `contact_co` function is held to the throw roles (spec CS2)."""
    codes = _changeover_codes(tmp_path, kind="contact_no", roles=("common", "break", "make"))
    assert codes.isdisjoint({"CHANGEOVER_ROLE", "CHANGEOVER_LINK"})
    generic = _changeover_codes(tmp_path, kind="contact_no", roles=("generic",) * 3)
    assert generic.isdisjoint({"CHANGEOVER_ROLE", "CHANGEOVER_LINK"})


def test_changeover_symbol_port(tmp_path):
    """A `symbol_port` on a `contact_co` port is refused; the same part without it is clean."""
    with_symbol_port = _changeover().replace(
        '{ name = "14", role = "make" }', '{ name = "14", role = "make", symbol_port = "no" }'
    )
    root = _root(tmp_path, parts=_part_of(with_symbol_port))
    (finding,) = [f for f in _findings(root) if f.code == "CHANGEOVER_SYMBOL_PORT"]
    assert finding.severity is Severity.ERROR
    assert "'14'" in finding.message
    assert "CHANGEOVER_SYMBOL_PORT" not in _changeover_codes(tmp_path)


def test_a_symbol_port_on_another_kind_is_not_a_changeover_error(tmp_path):
    """Only a `contact_co` function is refused a `symbol_port` (spec CS3)."""
    no_contact = _changeover(kind="contact_no", roles=("generic",) * 3).replace(
        'ports = [{ name = "11", role = "generic" }',
        'symbol = "make-contact"\nports = [{ name = "11", role = "generic", symbol_port = "in" }',
    )
    assert "CHANGEOVER_SYMBOL_PORT" not in _codes(_root(tmp_path, parts=_part_of(no_contact)))


def test_the_demo_relay_part_lints_clean():
    """Its `contact_co` ports carry `common` / `break` / `make`, and it lints clean."""
    import demo_parts

    root = Path(demo_parts.__file__).parent
    relay = root / "parts" / "relay-2co-24vdc.toml"
    assert 'role = "common"' in relay.read_text()
    assert [f for f in _findings(root) if "relay-2co-24vdc.toml" in f.message] == []


def test_board_without_pcb(tmp_path):
    broken = _CLEAN_PART.replace('category = "generic"', 'category = "board"')
    root = _root(tmp_path, parts={"p.toml": broken})
    findings = _findings(root)
    board = [f for f in findings if f.code == "BOARD_WITHOUT_PCB"]
    assert len(board) == 1
    assert board[0].severity is Severity.WARNING
    part_line = next(
        i for i, line in enumerate(broken.splitlines(), start=1) if line.strip() == "[part]"
    )
    assert board[0].message.startswith(f"parts/p.toml:{part_line}:")
    clean = broken.replace('class_code = "X"', 'class_code = "X"\n\n[pcb]\nrevision = "A"')
    assert "BOARD_WITHOUT_PCB" not in _codes(_root(tmp_path, parts={"p.toml": clean}))


def test_file_name(tmp_path):
    findings = _findings(_root(tmp_path, parts={"Bad Name.toml": _CLEAN_PART}))
    bad = [f for f in findings if f.code == "FILE_NAME"]
    assert len(bad) == 1
    assert bad[0].severity is Severity.WARNING
    assert "FILE_NAME" not in _codes(_root(tmp_path, parts={"good-name.toml": _CLEAN_PART}))


def test_every_finding_message_carries_a_file_and_line(tmp_path):
    """P6: every finding's message names its file and line, not only its subjects."""
    broken = _CLEAN_PART.replace('class_code = "X"', "class_code = 1")
    findings = _findings(_root(tmp_path, parts={"p.toml": broken}))
    assert findings
    for f in findings:
        assert f.subjects == ()
        assert ".toml:" in f.message


@pytest.mark.parametrize(
    ("link_kind", "fires"), [("switched", True), ("protective", False), ("conductive", False)]
)
def test_protection_link_kind(tmp_path, link_kind, fires):
    """A fuse or breaker is closed in service: a `switched` link is wrong, the other two pass."""
    function = _changeover(kind="protection", links=[("11", "12")]).replace("switched", link_kind)
    found = [
        f
        for f in _findings(_root(tmp_path, parts=_part_of(function)))
        if f.code == "PROTECTION_LINK_KIND"
    ]
    assert [f.severity for f in found] == ([Severity.ERROR] if fires else [])
