"""F1 (spec acceptance 3): the layout engine writes no `ext` key on any layout record.

Every fact the engine hands to render is a typed field of its record (model layout-namespace.md).
This test lays out the cabinet (contact images, replicas), the cabinet with a second location,
the narrow cabinet (pair markers), a PLC rack (item boxes) and the D10 and W3 stub fixtures
(off stubs, unit stand-ins, pin views), walks every derived layout record and fails if any of
them holds a non-empty `ext`. The generic `ext` field stays on the record for a consumer's own
use; the engine leaves it empty.

Can-fail, checked by probe: writing one `ext` key back in `write/` (`ext=frozendict(w=1)` on a
`Label`) fails `test_the_layout_engine_writes_no_ext_key[cabinet]`.
"""

import importlib.util
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from layout_cabinet import build_cabinet
from workspace_root import WORKSPACE_ROOT

from fransys_layout.engines import lay_out_schematic
from fransys_model.kernel import freeze
from fransys_model.layout import CABLE_KINDS, DERIVED_KINDS, layout_of

_ROOT_TESTS = WORKSPACE_ROOT / "tests"


def _load(name: str):
    """A root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], _ROOT_TESTS / name)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_STUBS = _load("test_dd_units_stubs.py")
_RACK = _load("test_dd_rack_boxes.py")


def _load_usecases():
    """The layout usecases module, loaded by path: its narrow cabinet has pair markers."""
    path = Path(__file__).parents[1] / "usecases" / "test_usecases.py"
    spec = importlib.util.spec_from_file_location("usecases_for_no_ext", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_USECASES = _load_usecases()


@cache
def _cabinet():
    return lay_out_schematic(freeze(build_cabinet()))[0]


@cache
def _cabinet_two_location():
    return lay_out_schematic(freeze(build_cabinet(second_location=True)))[0]


_FIXTURES = {
    "cabinet": _cabinet,
    "cabinet-two-location": _cabinet_two_location,
    "cabinet-narrow": _USECASES._narrow_laid_out,
    "plc-modules": _RACK._plc_modules,
    "unit-stub": _STUBS._off_stub_model,
    "system": _STUBS._system_model,
    "two-connectors": lambda: _STUBS._build_two_connectors(relay_between=True),
    "two-location-cable": _STUBS._two_location_cable_model,
}


def _ext_keys(model) -> dict[str, set[str]]:
    """Every `ext` key the engine wrote, by layout kind."""
    found: dict[str, set[str]] = {}
    for kind in (*DERIVED_KINDS, *CABLE_KINDS):
        record_type: type[Any] = kind  # every derived kind has the generic `ext` field
        keys = {key for record in layout_of(model, record_type).values() for key in record.ext}
        if keys:
            found[kind.__name__] = keys
    return found


@pytest.mark.parametrize("name", list(_FIXTURES))
def test_the_layout_engine_writes_no_ext_key(name: str) -> None:
    model = _FIXTURES[name]()
    assert sum(len(layout_of(model, kind)) for kind in DERIVED_KINDS) > 0
    assert _ext_keys(model) == {}


def test_the_fixtures_draw_every_record_kind_that_used_to_carry_ext() -> None:
    """The check is not vacuous: symbol placements, link markers (pair and star) and labels
    (contact images) all occur among the fixtures.
    """
    from fransys_model.layout import (
        Label,
        LinkMarker,
        PlacementView,
        StarKind,
        SymbolPlacement,
    )

    models = [build() for build in _FIXTURES.values()]
    placements = [p for m in models for p in layout_of(m, SymbolPlacement).values()]
    assert any(p.view is PlacementView.ITEM and p.ports for p in placements)
    assert any(p.view is PlacementView.PIN for p in placements)
    labels = [label for m in models for label in layout_of(m, Label).values()]
    assert any(label.slot == "contacts" for label in labels)
    markers = [marker for m in models for marker in layout_of(m, LinkMarker).values()]
    assert any(marker.star is None for marker in markers)
    assert any(marker.star is StarKind.OFF for marker in markers)
    assert any(marker.star is StarKind.REF for marker in markers)
    assert any(marker.box_x is not None or marker.stub_extra for marker in markers)
