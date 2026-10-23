"""`d.layout.pins_below` writes one `PinsBelowHint` per function of a box (BOX-SIDES).

Can-fail probes: write the hint twice in `hint_pins_below` and the one-record test fails; drop the
repeat check and the repeat test fails.
"""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.kernel import freeze, merge
from fransys_model.layout import PinsBelowHint, layout_of

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


def _hints(d):
    return [r for r in d.draft().records() if isinstance(r, PinsBelowHint)]


def _box():
    d = design(pair_library(), place="C1")
    return d, d.device("X1", "DEMO-CONN-2P")


def test_a_device_writes_one_hint_per_function() -> None:
    d, x1 = _box()
    d.layout.pins_below(x1)
    assert {h.function for h in _hints(d)} == {f.id for f in x1._item.functions}


def test_the_hint_survives_freeze() -> None:
    d, x1 = _box()
    d.layout.pins_below(x1)
    model = freeze(merge(pair_library(), d.draft()))
    assert len(layout_of(model, PinsBelowHint)) == len(x1._item.functions)


def test_a_repeat_raises_naming_the_box() -> None:
    d, x1 = _box()
    d.layout.pins_below(x1)
    with pytest.raises(AuthorError, match=r"X1.*already has a pins-below hint"):
        d.layout.pins_below(x1)
    assert len(_hints(d)) == len(x1._item.functions)


@pytest.mark.parametrize("target", ["X1", None, 3])
def test_a_target_that_is_no_device_or_function_raises(target) -> None:
    d, _ = _box()
    with pytest.raises(AuthorError, match="takes a device or one of its functions"):
        d.layout.pins_below(target)
    assert not _hints(d)
