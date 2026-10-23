"""Field case: a device whose only function is an `actuator` with four numbered terminals.

The engineering shape: a four-core cable runs from a four-terminal strip to one device. The
device's part has one function of kind `actuator` with four generic ports named "1" to "4" and
no symbol choice of its own.

The bug (v0.21.1): the core picks the three-phase motor symbol for the function and then refuses
the page: PLACEMENT_PROBLEM ERROR "port 3: no free port on symbol motor-3ph-pe", so the build
raises on write. v0.20 drew the function as a labelled generic box.
The ruling (R477 8.1, R479): the actuator row matches only the 3-phase port shape; any other
shape draws the labelled box, which is also chosen as `generic-box`.

Covered by: LIBRARY-SYMBOL (a symbol row matches kind and port shape, R477 8.1, R479) - fransys-el.
Decision: el-0062.
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_layout.geometry import GENERIC_BOX_KEY

sys.path.insert(0, str(Path(__file__).parent / "data"))  # the invented actuator part


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Valve", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    q1 = d.device("Q1", "DEMO-ACT-4T")
    for n in range(1, 5):
        w1.core(n, x1[n], q1.actuator[n])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Valve\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_the_actuator_device_draws_as_a_labelled_box_with_no_error() -> None:
    result = _built()
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
    symbols = [s for drawing in drawn_pages(result.model).values() for s in drawing.symbols]
    texts = [t.text for drawing in drawn_pages(result.model).values() for t in drawing.texts]
    assert [s.key for s in symbols if s.key == GENERIC_BOX_KEY] == [GENERIC_BOX_KEY]
    assert "-Q1" in texts


def test_the_box_is_chosen_by_its_public_key_generic_box() -> None:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Valve", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    q1 = d.device("Q1", "DEMO-ACT-4T")
    for n in range(1, 5):
        w1.core(n, x1[n], q1.actuator[n])
    d.layout.symbol(q1.actuator, GENERIC_BOX_KEY)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Valve\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    assert [f.code for f in result.findings if f.severity == fr.Severity.ERROR] == []
    keys = [s.key for dr in drawn_pages(result.model).values() for s in dr.symbols]
    assert GENERIC_BOX_KEY in keys
