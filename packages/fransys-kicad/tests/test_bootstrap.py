"""Unit tests for `part_file_skeleton` and `python -m fransys_kicad` (spec P10).

Every KiCad symbol name and pin layout here is invented (CLAUDE.md invariant 6): the
`DEMO-` prefix marks it, the way `examples/demo-parts` marks its invented parts.
"""

import tomllib

import pytest
from fransys_kicad.__main__ import main
from fransys_kicad.bootstrap import part_file_skeleton

pytestmark = pytest.mark.wp("kicad")


def _kicad_sym(symbol: str, units: dict[str, list[str]]) -> str:
    """A minimal `.kicad_sym` library with one symbol, invented for these tests.

    `units` maps a `"<unit>_<style>"` sub-symbol suffix (e.g. `"1_1"`) to the pin numbers
    of that sub-symbol, the way KiCad nests one sub-symbol per unit and body style under
    the top-level `(symbol "<name>" ...)`.
    """
    sub_symbols = "".join(
        f'(symbol "{symbol}_{suffix}" '
        + "".join(f'(pin passive line (number "{number}" (effects (font))))' for number in pins)
        + ")"
        for suffix, pins in units.items()
    )
    return f'(kicad_symbol_lib (version 1) (symbol "{symbol}" {sub_symbols}))'


def test_one_function_one_port_per_pin():
    kicad_sym = _kicad_sym("DEMO-CONN-3P", {"1_1": ["1", "2", "3"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-CONN-3P")
    assert skeleton.count("[[function]]") == 1
    assert skeleton.count('kind = "generic"') == 1
    for pin in ("1", "2", "3"):
        assert f'name = "{pin}", role = "generic"' in skeleton


def test_pins_from_every_unit_of_a_multi_unit_symbol_are_gathered():
    """A relay-like symbol: unit 1 is the coil, unit 2 the contact. Both units' pins appear."""
    kicad_sym = _kicad_sym("DEMO-RLY-2U", {"1_1": ["A1", "A2"], "2_1": ["1", "2", "3"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-RLY-2U")
    for pin in ("A1", "A2", "1", "2", "3"):
        assert f'name = "{pin}"' in skeleton
    assert skeleton.count('role = "generic"') == 5


def test_alternate_body_style_does_not_duplicate_pins():
    """Style 2 (KiCad's alternate/De Morgan body) repeats style 1's pin numbers; read once."""
    kicad_sym = _kicad_sym("DEMO-GATE-ALT", {"1_1": ["1", "2", "3"], "1_2": ["1", "2", "3"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-GATE-ALT")
    assert skeleton.count('role = "generic"') == 3


def test_a_unit_label_containing_its_own_underscore_is_not_double_counted():
    """Unit "1_2" (its own label has an underscore) still keeps one body style, not both."""
    kicad_sym = _kicad_sym("DEMO-UNDERSCORE-UNIT", {"1_2_1": ["1", "2"], "1_2_2": ["1", "2"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-UNDERSCORE-UNIT")
    assert skeleton.count('role = "generic"') == 2


def test_pin_order_is_kicad_file_order_not_sorted():
    """Pins are declared out of numeric and lexical order; the skeleton keeps that order."""
    kicad_sym = _kicad_sym("DEMO-ORDER", {"1_1": ["10", "2", "1"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-ORDER")
    assert (
        skeleton.index('name = "10"') < skeleton.index('name = "2"') < skeleton.index('name = "1"')
    )


def test_two_runs_on_the_same_input_are_byte_identical():
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    first = part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
    second = part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
    assert first == second


def test_a_pin_with_no_number_is_skipped_not_crashed_on():
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-NONUM" (symbol "DEMO-NONUM_1_1" '
        '(pin passive line (name "~" (effects (font)))) '
        '(pin passive line (number "1" (effects (font)))))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-NONUM")
    assert skeleton.count('role = "generic"') == 1
    assert 'name = "1"' in skeleton


def test_a_nested_symbol_with_a_nonconforming_name_still_yields_its_pins():
    """A sub-symbol not named `<top>_<unit>_<style>` is still walked for pins (not filtered)."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-ODD" (symbol "unrelated_name" '
        '(pin passive line (number "9" (effects (font)))))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-ODD")
    assert 'name = "9"' in skeleton


def test_a_pin_with_a_kicad_name_gets_a_marking():
    """model-0053 (F2): a pin's KiCad name becomes its port's `marking`."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-MARK" (symbol "DEMO-MARK_1_1" '
        '(pin passive line (name "A1" (effects (font))) (number "1" (effects (font)))))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-MARK")
    assert 'name = "1", role = "generic", marking = "A1" },' in skeleton


def test_a_pin_with_kicads_no_name_convention_gets_no_marking():
    """KiCad's `"~"` means "no name"; the skeleton leaves `marking` out, not `marking = "~"`."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-NOMARK" (symbol "DEMO-NOMARK_1_1" '
        '(pin passive line (name "~" (effects (font))) (number "1" (effects (font)))))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-NOMARK")
    assert 'name = "1", role = "generic" },' in skeleton
    assert "marking" not in skeleton


def test_a_marking_with_a_backslash_a_quote_and_a_newline_round_trips_through_toml():
    """A KiCad pin name is carried over verbatim (F2); the skeleton must still be valid TOML."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-ESCAPE" (symbol "DEMO-ESCAPE_1_1" '
        "(pin passive line (name "
        r'"ba\\ck\"slash"'
        " (effects (font))) "
        '(number "1" (effects (font)))) '
        "(pin passive line (name "
        r'"line1\nline2"'
        " (effects (font))) "
        '(number "2" (effects (font))))'
        ")))"
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-ESCAPE")
    ports = tomllib.loads(skeleton)["function"][0]["ports"]
    markings = {port["name"]: port["marking"] for port in ports}
    assert markings["1"] == 'ba\\ck"slash'
    assert markings["2"] == "line1\nline2"


def test_unknown_symbol_names_the_symbol_in_the_error():
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    with pytest.raises(ValueError, match="DEMO-MISSING"):
        part_file_skeleton(kicad_sym, "DEMO-MISSING")


def test_the_wrong_root_error_message_has_no_stray_characters():
    """The exact message, not just a substring match, so a mangled literal cannot slip by."""
    kicad_sym = '(not_kicad_symbol_lib (symbol "X"))'
    with pytest.raises(ValueError, match="not a parsable KiCad symbol library") as excinfo:
        part_file_skeleton(kicad_sym, "X")
    assert str(excinfo.value) == (
        "not a parsable KiCad symbol library: expected a kicad_symbol_lib root"
    )


def test_a_non_symbol_node_matching_the_name_is_not_mistaken_for_the_symbol():
    """Only a `(symbol "<name>" ...)` node counts; another tag sharing that text does not."""
    kicad_sym = (
        '(kicad_symbol_lib (comment "DEMO-BAR") (symbol "DEMO-REAL" '
        '(pin passive line (number "1" (effects (font))))))'
    )
    with pytest.raises(ValueError, match="DEMO-BAR"):
        part_file_skeleton(kicad_sym, "DEMO-BAR")


def test_a_symbol_with_no_pins_yields_an_empty_port_list():
    kicad_sym = '(kicad_symbol_lib (symbol "DEMO-EMPTY"))'
    skeleton = part_file_skeleton(kicad_sym, "DEMO-EMPTY")
    assert "role" not in skeleton
    assert "ports = [\n]" in skeleton


def test_a_pin_missing_its_electrical_type_and_style_fields_still_reads_its_number():
    """`(pin ...)` is walked generically; a pin lacking those two leading fields still counts."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-MIN" (symbol "DEMO-MIN_1_1" '
        '(pin (number "1" (effects (font)))))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-MIN")
    assert 'name = "1", role = "generic"' in skeleton


def test_a_number_tag_with_no_trailing_children_still_reads_its_value():
    """`(number "1")` with no nested `(effects ...)` still has a value, per _TAGGED_LEN."""
    kicad_sym = (
        '(kicad_symbol_lib (symbol "DEMO-NOEFF" (symbol "DEMO-NOEFF_1_1" '
        '(pin passive line (number "1")))))'
    )
    skeleton = part_file_skeleton(kicad_sym, "DEMO-NOEFF")
    assert 'name = "1", role = "generic"' in skeleton


@pytest.mark.parametrize(
    "kicad_sym",
    [
        pytest.param("", id="empty"),
        pytest.param("not-an-sexpr", id="no-parens"),
        pytest.param('(kicad_symbol_lib (symbol "X"', id="unclosed-paren"),
        pytest.param('(a "b', id="unterminated-string"),
        pytest.param("(kicad_symbol_lib) (extra)", id="trailing-text"),
        pytest.param('(not_kicad_symbol_lib (symbol "X"))', id="wrong-root"),
    ],
)
def test_unparsable_or_wrong_shaped_text_raises(kicad_sym):
    with pytest.raises(ValueError, match="not a parsable KiCad symbol library"):
        part_file_skeleton(kicad_sym, "X")


def test_main_reads_the_file_and_writes_the_skeleton_to_stdout(tmp_path, capsys):
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    library_path = tmp_path / "demo.kicad_sym"
    library_path.write_text(kicad_sym, encoding="utf-8")
    exit_code = main([str(library_path), "DEMO-CONN-2P"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
