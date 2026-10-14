"""One can-fail test and one clean twin per lint code.

Every test builds a small library in `tmp_path`: a `library.toml` and, unless a test is
about `library.toml` itself, one part file under `parts/`. `_codes` reads back the set of
finding codes `lint` returned, so a test checks exactly the code (and severity) its check
owns, not incidental noise from the rest of the file.
"""

import itertools

import fransys_parts

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


def test_multiline_string(tmp_path):
    """The check is made on the parsed value, so a genuine embedded line break is needed."""
    broken = _CLEAN_PART.replace('description = "d"', 'description = """line one\nline two"""')
    root = _root(tmp_path, parts={"p.toml": broken})
    assert "MULTILINE_STRING" in _codes(root)
    assert "MULTILINE_STRING" not in _codes(_root(tmp_path))


def test_links_with_no_ports_key_reports_link_port_unknown_not_a_crash(tmp_path):
    """A function with `links` but no `ports` key at all must not crash `_check_links`."""
    part = _PART_HEAD + '[[function]]\nname = "f1"\nkind = "generic"\n' + _LINK_1_2 + "\n"
    root = _root(tmp_path, parts={"p.toml": part})
    findings = _findings(root)
    assert "LINK_PORT_UNKNOWN" in {f.code for f in findings}


_CABLE_PRODUCT = (
    "[cable_product]\n"
    'core_count = 3\ncore_colours = ["BN", "BK"]\ngauge_mm2 = "1.5"\nshielded = false'
)


_CABLE_PRODUCT_ONE_CORE = (
    '[cable_product]\ncore_count = 1\ncore_colours = ["BN"]\ngauge_mm2 = "1.5"\nshielded = false'
)


_PART_HEAD = _CLEAN_PART[: _CLEAN_PART.index("[[function]]")]


def _function(name, kind, marking=None):
    """One `[[function]]` with the port `1`; a connector gets its facet, `marking` if given."""
    text = f'[[function]]\nname = "{name}"\nkind = "{kind}"\n{_ONE_PORT}\n'
    if kind == "connector":
        text += '\n[function.connector]\nstyle = "s"\npincount = 1\ngender = "male"\n'
        if marking is not None:
            text += f"marking = {marking}\n"
    return text + "\n"


_SIX_CORES = '["WH", "BN", "WH", "BN", "SH", "SH"]'


def _pair_part(pairs, colours=_SIX_CORES):
    """A cable part whose `[cable_product]` carries `pairs` (inline-table text) over six cores."""
    cable = _CLEAN_PART.replace('category = "generic"', 'category = "cable"')
    return (
        cable + "\n[cable_product]\n"
        f'core_count = 6\ncore_colours = {colours}\ngauge_mm2 = "0.75"\nshielded = false\n'
        f"pairs = {pairs}\n"
    )


def _pair_codes(tmp_path, pairs, colours=_SIX_CORES):
    return _codes(_root(tmp_path, parts={"p.toml": _pair_part(pairs, colours)}))


def test_cable_pair_valid_gives_no_pair_finding(tmp_path):
    """Two pairs with screens 5 and 6, and an `SH` core (none here) named by no pair is fine."""
    valid = "[{ cores = [1, 2], screen = 5 }, { cores = [3, 4], screen = 6 }]"
    assert "CABLE_PAIR_INVALID" not in _pair_codes(tmp_path, valid)


def test_cable_pair_core_out_of_range(tmp_path):
    # MUTATION: drop the `core <= len(colours)` bound, so core 7 passes as a valid index
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, "[{ cores = [1, 7] }]")


def test_cable_pair_not_two_cores(tmp_path):
    # MUTATION: accept any length of `cores`, so a three-core pair passes
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, "[{ cores = [1, 2, 3] }]")


def test_cable_pair_core_in_two_pairs(tmp_path):
    # MUTATION: count each pair's cores separately, so core 2 named by two pairs passes
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, "[{ cores = [1, 2] }, { cores = [2, 4] }]")


def test_cable_pair_core_is_sh(tmp_path):
    # MUTATION: skip the `colours[core - 1] == "SH"` test, so core 5 (SH) in a pair passes
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, "[{ cores = [1, 5] }]")


def test_cable_pair_screen_not_sh(tmp_path):
    # MUTATION: stop checking the screen's colour, so core 3 (WH) as a screen passes
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, "[{ cores = [1, 2], screen = 3 }]")


def test_cable_pair_screen_named_twice(tmp_path):
    # MUTATION: drop the `_repeated(screens)` report, so SH core 5 named by two pairs passes
    pairs = "[{ cores = [1, 2], screen = 5 }, { cores = [3, 4], screen = 5 }]"
    assert "CABLE_PAIR_INVALID" in _pair_codes(tmp_path, pairs)
