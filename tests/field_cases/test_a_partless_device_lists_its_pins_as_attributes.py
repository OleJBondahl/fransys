"""Field case: equipment another party supplies is wired by pin letter, with no part file behind it.

The engineering shape: an external unit E1 (a meter or a remote panel) arrives with its own
terminals U, V and W. The design names it with no part number, and the wiring is drawn to
those pin letters.

The bug: a part's device exposes each pin as an attribute, so tab completion and type checkers
see `d.device(...).U`. A part-less device returned a Port for `ext.U` at runtime, but `dir(ext)`
listed no pin, so completion and type checkers saw only Any.

Decision (author-0061, item 1): a part-less device lists each of its pins in `dir()`, as a
part's device does. `ext["U"]` keeps working.
"""

import fransys as fr


def test_dir_lists_each_pin() -> None:
    """`dir()` of a part-less device names each of its pins."""
    d = fr.design("demo_parts")
    ext = d.device("E1", None, external=True, pins=("U", "V", "W"))
    assert {"U", "V", "W"} <= set(dir(ext))


def test_attribute_and_item_give_the_same_pin() -> None:
    """`ext.U` and `ext["U"]` are the same Port, and the attribute can start a series."""
    d = fr.design("demo_parts")
    ext = d.device("E1", None, external=True, pins=("U", "V", "W"))
    assert ext.U is ext["U"]
