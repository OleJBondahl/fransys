"""CUT-TALL: a column more than two pages tall is cut into as many pieces as it needs."""

from __future__ import annotations

import pytest

from fransys_layout.core.values import RefKind

from .cut_fixtures import chain, cut_of, elem

PAGE_H = 822


@pytest.mark.rule("PAGE-CUT")
def test_a_column_of_four_pages_is_cut_into_pieces_that_each_fit_one() -> None:
    """Thirty cells of 96 G stack to 3112 G: no two cuts make the pieces fit, so there are more."""
    ids = [f"k{i:02d}" for i in range(30)]
    result = cut_of([elem(i, 40, 96) for i in ids], chain(ids))
    columns = result.flow.columns
    assert [c.id for c in columns] == [f"c:k00#{chr(97 + k)}" for k in range(len(columns))]
    assert len(columns) >= 4
    assert all(c.height <= PAGE_H for c in columns)
    assert [cell.sym for c in columns for cell in c.lanes[0].cells] == ids
    tags = [r for r in result.spec.reference_plan if r.kind is RefKind.TAG]
    assert len(tags) == len(columns) - 1
    assert not [f for f in result.spec.findings if f.code == "PAGE_OVERFLOW"]
