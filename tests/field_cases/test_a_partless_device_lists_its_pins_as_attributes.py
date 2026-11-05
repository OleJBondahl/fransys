"""Field case: equipment another party supplies, an external unit E1 with pins U, V and W, wired by pin letter with no part file.
The bug: `ext.U` worked at runtime, but dir(ext) of a part-less device listed no pin, so type checkers saw only Any.
Fixed by author-0061 (item 1), a part-less device lists each of its pins in `dir()` as a part's device does; `ext["U"]` keeps working."""

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
