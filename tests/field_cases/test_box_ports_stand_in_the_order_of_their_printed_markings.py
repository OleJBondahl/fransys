"""Field case: a box's ports stand in the order of their printed markings, not of their function.

The engineering shape: an e-stop relay with no symbol of its own draws as a generic box. Its
safety channels are two functions, `chan_b` (terminals S11 and S12) and `chan_a` (S21 and S22).
The coil is wired to a lamp; the channel terminals are not wired yet.

The bug: the terminals nobody ordered took their rank inside their own function only, so the
two functions' first terminals tied and the box read S11 S21 S22 S12.
The rule (decision layout-0250): ports nobody ordered stand in the natural order of their printed
markings and each function's ports stay together, so the unwired terminals read S11 S12 S21 S22;
the wired coil pin A1 still leads and A1 stays over A2.
"""

import tempfile
from pathlib import Path

import fransys as fr
import fransys_parts
from fransys.colours import BU

from fransys_model.kernel import merge

_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_PART = """schema = 1

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


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


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
    d.detail.wire(relay.coil["A1"], d.device("P1", "DEMO-LAMP-24")[1], wire=(BU, 0.5))
    (root / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=root / "cover.md")
    model = fr.build(d, doc).model
    (box,) = (
        one
        for one in _gap(model, "symbol subject")
        if one.key == "generic-box" and one.owner.startswith("K1 ")
    )
    offsets, sides = dict(box.offsets), dict(box.sides)
    drawn = sorted(offsets, key=lambda name: (offsets[name], sides[name] != "n"))
    return [name.rsplit(".", 1)[-1] for name in drawn]


def test_an_estop_relay_box_reads_its_terminals_in_marking_order() -> None:
    """The coil pin A1 is wired, so it leads; the four unwired terminals follow in marking order."""
    order = _box_marking_order()
    assert order[0] == "A1"
    assert [m for m in order if m.startswith("S")] == ["S11", "S12", "S21", "S22"]
