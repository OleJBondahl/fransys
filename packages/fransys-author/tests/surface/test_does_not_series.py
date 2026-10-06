"""EA13 for the series, supply, cable and strip calls: classes reached only as return values."""

from fransys_author.surface._cable import Cable, Cables
from fransys_author.surface._series import Series
from fransys_author.surface._supplies import AcSupply, DcSupply, Supplies, SupplyRail, _Rails

from .test_does_not_lines import has_does_not

_CALLS = (
    (Series, "series"),
    (Series, "parallel"),
    (Supplies, "ac_supply"),
    (Supplies, "dc_supply"),
    (Cables, "cable"),
    (Cable, "core"),
    (_Rails, "__getattr__"),
)
_CLASSES = (AcSupply, DcSupply, SupplyRail, Cable)


def test_each_new_call_and_handle_says_what_it_does_not_do() -> None:
    missing = [f"{c.__name__}.{n}" for c, n in _CALLS if not has_does_not(getattr(c, n).__doc__)]
    missing += [c.__name__ for c in _CLASSES if not has_does_not(c.__doc__)]
    assert not has_does_not(None)
    assert not missing, f"no 'Does not' line: {missing}"
