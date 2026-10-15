"""Field case: a cable whose cores land on two contact blocks of one e-stop head.

The engineering shape: an e-stop head `S1` with two break-contact blocks clipped on with
`parent=`, each in its own circuit. One 4-core cable joins both blocks to a terminal strip. An
electrician reads one device, `S1`, at that end of the cable.

The bug: each block was its own cable end, both printing `S1`, so the build raised
HARNESS_END_AMBIGUOUS and its text pointed at units and strips.

Rule: the cable's end is the device that prints the label (`designation_holder`), so the two
blocks are one end with both pins landed on it. Decision: API-FRICTION-1 F9. Invented parts from
`demo_parts`: `DEMO-HEAD-ESTOP`, `DEMO-BLOCK-1NC`, `DEMO-BLOCK-1NC-21`, `DEMO-CBL-4G1.5`.
"""

import fransys as fr
from _model_build_cover import cabinet_document

from fransys_model.derive.block_diagram import diagram_lines


def _built():
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    head = d.device("S1", "DEMO-HEAD-ESTOP")
    first = d.device(None, "DEMO-BLOCK-1NC", name="block-1", parent=head)
    second = d.device(None, "DEMO-BLOCK-1NC-21", name="block-2", parent=head)
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, strip[1], first["11"])
    cable.core(2, strip[2], first["12"])
    cable.core(3, strip[3], second["21"])
    cable.core(4, strip[4], second["22"])
    return d, head, strip, fr.build(d, cabinet_document(cabinet))


def test_two_blocks_of_one_head_are_one_cable_end() -> None:
    _, _, _, built = _built()
    model = built.model
    assert "HARNESS_END_AMBIGUOUS" not in {f.code for f in built.findings}
    (harness,) = fr.derive.top_level_cables(model)
    assert sorted(len(end.pins) for end in harness.ends) == [4, 4]
    assert {end.designation for end in harness.ends} == {"+CAB-S1", "+CAB-X1"}


def test_the_block_diagram_joins_the_head_box_to_the_strip_box() -> None:
    """The system diagram draws one line between the head and the strip, never a block as a box."""
    _, head, _strip, built = _built()
    (line,) = diagram_lines(built.model, None)
    assert head.id in {line.a, line.b}
    (other,) = {line.a, line.b} - {head.id}
    assert fr.derive.item_designation(built.model, other).endswith("X1")
