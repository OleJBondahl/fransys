"""A change list names a boundary's ports in marking order: `A2` before `A10` (model-0153)."""

from fransys_model.derive.baseline_diff_units import _boundary_changes
from fransys_model.derive.rows import BaselineBoundary


def _boundary(*ports: str) -> BaselineBoundary:
    return BaselineBoundary(designation="X1", ports=ports, rating=None, operating=None)


def test_ports_in_a_change_list_sort_by_marking_not_by_string() -> None:
    gone = _boundary("A10", "A2")
    (removed,) = _boundary_changes((gone,), (), "U")
    assert removed.detail == "ports A2, A10"
    (added,) = _boundary_changes((), (gone,), "U")
    assert added.detail == "ports A2, A10"
    grown = _boundary_changes((_boundary("A1"),), (_boundary("A1", "A10", "A2"),), "U")
    assert [c.after for c in grown] == ["A2", "A10"]
    shrunk = _boundary_changes((_boundary("A1", "A10", "A2"),), (_boundary("A1"),), "U")
    assert [c.before for c in shrunk] == ["A2", "A10"]
