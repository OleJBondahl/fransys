import dataclasses
from pathlib import Path

import fransys_parts
import pytest
from fransys_kicad import check, netlist, part_file_skeleton

from fransys_model.vocab.tables import items

GOLDEN = Path(__file__).resolve().parent / "golden" / "board.net"

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


def _library(tmp_path: Path, part_text: str, *, name: str = "demo-conn-2p.toml") -> Path:
    """A one-part library in `tmp_path`, ready for `fransys_parts.lint`."""
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library.toml").write_text(
        'schema = 1\nname = "kicad-skeleton-demo"\nversion = "0.1.0"\ndescription = "d"\n',
        encoding="utf-8",
    )
    parts_dir = root / "parts"
    parts_dir.mkdir()
    (parts_dir / name).write_text(part_text, encoding="utf-8")
    return root


_FILLED = {
    'mpn = ""  # TODO: fill in': 'mpn = "DEMO-CONN-2P-001"',
    'manufacturer = ""  # TODO: fill in': 'manufacturer = "Demo"',
    'description = ""  # TODO: fill in': 'description = "Invented 2-pin connector"',
    'category = ""  # TODO: fill in': 'category = "generic"',
    'class_code = ""  # TODO: fill in': 'class_code = "X"',
}


def test_skeleton_lint_trips_only_the_human_fields(tmp_path):
    """The raw skeleton lints clean except the fields P10 says a human must fill."""
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
    root = _library(tmp_path, skeleton)
    codes = {finding.code for finding in fransys_parts.lint(root)}
    assert codes == {"CLASS_CODE", "ENUM_VALUE"}


def test_skeleton_twin_with_human_fields_filled_lints_clean(tmp_path):
    """Filling in the five human fields makes the skeleton lint clean: it was otherwise correct."""
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
    for placeholder, filled in _FILLED.items():
        assert placeholder in skeleton
        skeleton = skeleton.replace(placeholder, filled)
    root = _library(tmp_path, skeleton)
    assert fransys_parts.lint(root) == ()


def test_netlist_matches_golden(demo_board):
    text = netlist(demo_board.freeze(), demo_board.board.item)
    assert text == GOLDEN.read_text(encoding="utf-8")


def test_timestamps_stable_across_unrelated_edit(demo_board, edit):
    model = demo_board.freeze()
    board = demo_board.board.item
    before = netlist(model, board)
    an_item = next(iter(items(model).values()))
    edited_item = dataclasses.replace(an_item, description=an_item.description + " (edited)")
    edited_model = edit(model, edited_item)
    after = netlist(edited_model, board)
    assert before == after


def test_unconnected_pin_is_a_finding(demo_board):
    findings = check(demo_board.freeze(), demo_board.board.item)
    assert any(f.code == "UNCONNECTED_PIN" for f in findings)


def test_skeleton_lists_every_pin():
    """One `[[function]]`, one port per pin (spec P10; P1's ports are inline, not a table)."""
    kicad_sym = _kicad_sym("DEMO-CONN-2P", {"1_1": ["1", "2"]})
    skeleton = part_file_skeleton(kicad_sym, "DEMO-CONN-2P")
    assert skeleton.count("[[function]]") == 1
    assert skeleton.count('role = "generic"') == 2
