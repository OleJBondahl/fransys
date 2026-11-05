"""Field case: an unchanged I/O unit is released at revision 2 over a revision 1 stored at listing version 1.
The bug: fr.release raised INTERFACE_NOT_BUMPED, as the facade compared boundaries field for field across listing v1 and v2.
Fixed by model-0307, derive.boundary_changed compares only the fields the previous listing's version carries."""

from typing import Any
lazy from pathlib import Path

import fransys as fr
from _field_designs import io
from stale_releases import cut_old, unit_id

from fransys_model.derive import baseline

_FIRST = fr.unit("demo-io", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
_SECOND = fr.unit("demo-io", revision=2, interface_version=1, date="2026-02-01", text="again", by="AB")


def _build(unit_fn: Any) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(unit_fn(io), "U1")
    return fr.build(d)


def test_an_unchanged_unit_released_over_a_listing_v1_does_not_bump_its_interface(
    tmp_path: Path,
) -> None:
    first = _build(_FIRST)
    folder = fr.release(first, tmp_path, unit="demo-io")
    old = baseline.listing(first.model, unit_id(first, "demo-io"))
    cut_old(folder, first, "demo-io", "0.19.6", old)
    fr.release(_build(_SECOND), tmp_path, unit="demo-io")
