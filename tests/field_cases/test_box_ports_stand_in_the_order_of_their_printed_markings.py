"""Field case: an e-stop relay with no symbol of its own, drawn as a generic box with safety channels chan_b and chan_a.
The bug: unordered terminals ranked only inside their own function, so the first terminals tied and the box read S11 S21 S22 S12.
Fixed by layout-0250, unordered ports stand in the natural order of their printed markings and each function's ports stay together."""

import tempfile
from pathlib import Path

import fransys as fr
import fransys_parts
from _drawn_facts import symbol_subjects
from fransys.colours import BU

from fransys_model.kernel import merge

_LIBRARY = 'schema = 2\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_PART = """schema = 2

[part]
mpn = "FLD-ESTOP-RELAY"
manufacturer = "Demo"
description = "E-stop relay, two safety channels on box terminals"
category = "generic"
class_code = "K"

[[function]]
name = "coil"
kind = "load"
ports = [{ name = "A1", role = "generic" }, { name = "A2", role = "generic" }]

[[function]]
name = "chan_b"
kind = "load"
ports = [{ name = "S11", role = "generic" }, { name = "S12", role = "generic" }]

[[function]]
name = "chan_a"
kind = "load"
ports = [{ name = "S21", role = "generic" }, { name = "S22", role = "generic" }]
"""


def _box_marking_order() -> list[str]:
    """The markings of the relay's box, left to right (N before S at one x)."""
    root = Path(tempfile.mkdtemp())
    (root / "parts").mkdir()
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "estop.toml").write_text(_PART)
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(root))
    d = fr.Design(draft, place="CAB")
    cab = d.location("CAB", "Cabinet")
    relay = d.device("K1", "FLD-ESTOP-RELAY")
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.series(relay.coil["A1"], lamp["1"], wire=(BU, 0.5))
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN")
    d.series(lamp["2"], strip[1], wire=(BU, 0.5))
    d.series(relay.coil["A2"], strip[1], wire=(BU, 0.5))
    (root / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=root / "cover.md")
    model = fr.build(d, doc).model
    (box,) = (one for one in symbol_subjects(model) if one.key == "generic-box" and one.tag == "K1")
    offsets, sides = dict(box.offsets), dict(box.sides)
    drawn = sorted(offsets, key=lambda name: (offsets[name], sides[name] != "n"))
    return [name.rsplit(".", 1)[-1] for name in drawn]


def test_an_estop_relay_box_reads_its_terminals_in_marking_order() -> None:
    """The coil pin A1 is wired, so it leads; the four unwired terminals follow in marking order."""
    order = _box_marking_order()
    assert order[0] == "A1"
    assert [m for m in order if m.startswith("S")] == ["S11", "S12", "S21", "S22"]
