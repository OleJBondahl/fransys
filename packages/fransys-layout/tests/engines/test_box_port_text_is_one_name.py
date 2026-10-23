"""SB8: derive's box port text equals the symbol side's box port name (KIT-FACTS A1).

`electrical_symbols` cannot import derive, so the text has two spellings; this holds them equal.
"""

import pytest

from fransys_layout.geometry import box_port_name
from fransys_model.derive.item_boxes import box_port_text


@pytest.mark.parametrize(("function", "port"), [("K1", "A1"), ("DI-1", "in"), ("", "x")])
def test_the_two_box_port_spellings_agree(function: str, port: str) -> None:
    assert box_port_text(function, port) == box_port_name(function, port)


def test_the_comparison_can_fail() -> None:
    assert box_port_text("K1", "A1") != box_port_name("K1", "A2")
