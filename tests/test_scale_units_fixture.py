"""Smoke test of the scale fixture: its unit, location and item counts are exact in N."""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest

from fransys_model.derive import unit_release
from fransys_model.derive.passes.numbering import REFERENCE_DESIGNATION_DUPLICATE
from fransys_model.kernel import Severity
from fransys_model.vocab.tables import items, units

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import (  # noqa: E402
    PROJECT,
    UNITS_PER_INSTANCE,
    build_scale,
    pump_cabinet,
)

ITEMS_PER_INSTANCE = 9  # X2 strip, 2 terminals, board, X1, K1, harness, P1, cable


@pytest.mark.parametrize("n", [2, 3])
def test_the_units_and_items_are_exact_in_n(n):
    # with_document=True: this test's own ERROR-absence check below would otherwise miss any
    # layout-only ERROR (e.g. SYMBOL_PORT_MISSING) since decision 0037 (PS1) never runs layout
    # without one; build_scale's own default stays document-free (acceptance 6).
    result = build_scale(n, with_document=True)
    model = result.model
    assert len(units(model)) == 1 + UNITS_PER_INSTANCE * n
    assert len(items(model)) == ITEMS_PER_INSTANCE * n
    for i in range(1, n + 1):
        own = [item for item in items(model).values() if item.key[0] == f"pump{i}"]
        assert len(own) == ITEMS_PER_INSTANCE
    codes = [f.code for f in result.findings]
    assert REFERENCE_DESIGNATION_DUPLICATE not in codes
    assert [f for f in result.findings if f.severity is Severity.ERROR] == []


@pytest.mark.parametrize("n", [2, 3])
def test_the_units_nest_container_then_cabinet_then_board(n):
    """One container, `n` cabinets under it, and under each cabinet its own one board unit."""
    model = build_scale(n).model
    all_units = units(model).values()
    (container,) = (u for u in all_units if unit_release(model, u.id).name == "scale-container")
    cabinets = [u for u in all_units if unit_release(model, u.id).name == "demo-pump-cabinet"]
    boards = [u for u in all_units if unit_release(model, u.id).name == "demo-io-board"]
    assert container.parent is None
    assert len(cabinets) == len(boards) == n
    assert {u.parent for u in cabinets} == {container.id}
    assert sorted(u.parent for u in boards if u.parent is not None) == sorted(
        u.id for u in cabinets
    )


def test_two_instances_sharing_one_location_name_are_a_duplicate_designation():
    """Can-fail of the no-duplicate check above: the same cabinets under one name do collide."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    container = d.unit("scale-container", revision=1, interface="1")
    container.revision(1, date="2026-01-01", text="First release", created="XX")
    for i in (1, 2):
        for terminal in pump_cabinet(container.scope(f"pump{i}", at=er), name="C1"):
            container.unused(terminal)
    codes = [f.code for f in fr.build(parts, d.draft()).findings]
    assert REFERENCE_DESIGNATION_DUPLICATE in codes


def test_one_more_instance_adds_exactly_one_instance():
    two = build_scale(2).model
    three = build_scale(3).model
    assert len(items(three)) - len(items(two)) == ITEMS_PER_INSTANCE
    assert len(units(three)) - len(units(two)) == UNITS_PER_INSTANCE
