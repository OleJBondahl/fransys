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


def _bar_part(symbol_line="", ports=None):
    """A bar function with `ports` (a TOML array), and `symbol_line` before it if given."""
    ports = ports if ports is not None else _bar_ports(20)
    return _PART_HEAD + f'[[function]]\nname = "pe"\nkind = "bar"\n{symbol_line}ports = {ports}\n'


def _bar_ports(count):
    """`count` PE ports named `1`..`count`, as one TOML array."""
    return "[" + ", ".join(f'{{ name = "{n}", role = "pe" }}' for n in range(1, count + 1)) + "]"


def test_bar_with_a_symbol_is_refused_and_the_message_names_the_fix(tmp_path):
    root = _root(tmp_path, parts={"p.toml": _bar_part('symbol = "terminal"\n')})
    (finding,) = [f for f in _findings(root) if f.code == "BAR_SYMBOL"]
    assert finding.severity is Severity.ERROR
    assert "a bar is never drawn: remove symbol" in finding.message
    assert "BAR_SYMBOL" not in _codes(_root(tmp_path, parts={"p.toml": _bar_part()}))


def test_bar_with_twenty_pe_ports_and_no_symbol_is_clean(tmp_path):
    root = _root(tmp_path, parts={"p.toml": _bar_part()})
    assert "BAR_SYMBOL" not in _codes(root)
    assert "FUNCTION_WITHOUT_PORTS" not in _codes(root)
    assert _codes(root) == set()


def test_cut_to_length_bar_with_no_ports_is_not_a_function_without_ports(tmp_path):
    root = _root(tmp_path, parts={"p.toml": _bar_part(ports="[]")})
    assert "FUNCTION_WITHOUT_PORTS" not in _codes(root)


def test_a_generic_function_with_no_ports_is_still_refused(tmp_path):
    part = _PART_HEAD + '[[function]]\nname = "f1"\nkind = "generic"\nports = []\n'
    assert "FUNCTION_WITHOUT_PORTS" in _codes(_root(tmp_path, parts={"p.toml": part}))


_OPERATED_HEAD = _PART_HEAD.replace(
    'class_code = "X"\n', 'class_code = "X"\noperated_by = "mushroom"\n'
)


def test_operated_by_head_without_function_lints_clean(tmp_path):
    """A head sold apart from its blocks states `operated_by` and has no `[[function]]`."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import OperatedBy, parts

    root = _root(tmp_path, parts={"p.toml": _OPERATED_HEAD})
    assert "ENUM_VALUE" not in _codes(root)
    assert not _findings(root)
    (part,) = parts(freeze(fransys_parts.load_path(root))).values()
    assert part.operated_by is OperatedBy.MUSHROOM


def test_operated_by_unknown_value_is_an_enum_error(tmp_path):
    """`pull` is not an `OperatedBy` value: the enum check reports it as an error."""
    root = _root(tmp_path, parts={"p.toml": _OPERATED_HEAD.replace('"mushroom"', '"pull"')})
    assert "ENUM_VALUE" in _codes(root)
    assert Severity.ERROR in {f.severity for f in _findings(root) if f.code == "ENUM_VALUE"}


def test_part_without_operated_by_loads_none(tmp_path):
    """A part that does not state `operated_by` loads with `None`: not stated."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import parts

    (part,) = parts(freeze(fransys_parts.load_path(_root(tmp_path)))).values()
    assert part.operated_by is None


def test_class_code_letter_rules_come_from_the_designation_scheme(tmp_path):
    """A, I, O are forbidden and D, L, V, Y, Z reserved (IEC 81346-2); X is clean (EL-9 part F)."""
    for code, rule in (
        ("A", "forbidden"),
        ("O", "forbidden"),
        ("D", "reserved"),
        ("Z", "reserved"),
    ):
        part = _CLEAN_PART.replace('class_code = "X"', f'class_code = "{code}"')
        found = [
            f for f in _findings(_root(tmp_path, parts={"p.toml": part})) if f.code == "CLASS_CODE"
        ]
        assert [rule in f.message for f in found] == [True], code
    assert "CLASS_CODE" not in _codes(_root(tmp_path))
