"""`terminal_strips`, `boards` and their unit forms list by natural designation (model-0153)."""

import fransys as fr

from fransys_model.derive import boards, item_designation, terminal_strips


def test_strips_and_boards_list_x2_before_x10_whatever_their_ids() -> None:
    d = fr.design("demo_parts", place="C1")
    for tag in ("X10", "X2", "X1"):
        d.terminal_strip(tag, "DEMO-TB-2.5", 1)
    for tag in ("A10", "A2", "A1"):
        d.device(tag, "DEMO-PCB-IO")
    model = fr.build(d).model
    assert [item_designation(model, s) for s in terminal_strips(model)] == ["X1", "X2", "X10"]
    assert [item_designation(model, b) for b in boards(model)] == ["A1", "A2", "A10"]
