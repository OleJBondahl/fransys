"""A stub of a by-others end is dashed and says so, in every mode (O10); other stubs are not."""

import pytest
from fold_builders import fold_plant

from fransys_model.derive import overview_view_rows
from fransys_model.derive.drawing_text import external_note
from fransys_model.layout import OverviewMode

_MODES = [OverviewMode.PLAIN, OverviewMode.GROUPS, OverviewMode.SEE_THROUGH]


def _stubs(rows) -> list:
    return [b for v in rows for b in v.boxes if b.key.at is not None]


@pytest.mark.parametrize("mode", _MODES)
def test_a_by_others_stub_is_dashed_and_says_so_while_the_others_are_not(mode) -> None:
    """Breaks if the by-others fact is dropped from the groups view or applied to every stub."""
    model, unit, _ = fold_plant(external=("b1",))
    rows = [v for v in overview_view_rows(model, unit) if v.mode is mode and v.level is None]
    stubs = _stubs(rows)
    others = [b for b in stubs if b.dashed]
    assert others
    assert all(b.lines[0] == f"-B1 ({external_note()})" for b in others)
    assert all(not b.dashed and external_note() not in b.lines[0] for b in stubs if b not in others)
    assert len(others) < len(stubs)


def test_with_nothing_by_others_no_stub_is_dashed() -> None:
    """Breaks if a stub is dashed by being a stub."""
    model, unit, _ = fold_plant()
    assert not [b for b in _stubs(overview_view_rows(model, unit)) if b.dashed]
