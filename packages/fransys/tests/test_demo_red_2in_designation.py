"""DEMO-RED-2IN is class R (IEC 81346-2: it restricts a flow); DEMO-RENAMES P2."""

import fransys as fr

from fransys_model import derive


def test_an_untagged_redundancy_module_prints_the_letter_r() -> None:
    d = fr.design("demo_parts", place="C")
    d.location("C", "Cab")
    d.device(None, "DEMO-RED-2IN", name="First")
    d.device(None, "DEMO-RED-2IN", name="Second")
    rows = derive.designation_list(fr.build(d).model)
    assert [r.designation for r in rows] == ["-R1", "-R2"]
