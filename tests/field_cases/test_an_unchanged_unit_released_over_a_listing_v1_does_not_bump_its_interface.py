"""Field case: a unit rebuilt unchanged is released over a previous release stored at listing v1.

The engineering shape: an I/O unit with one device and two interface connectors, released at
revision 1 by a fransys that wrote listing version 1 (no item keys), then rebuilt with nothing
changed and released at revision 2 under the same interface version.

The bug: `fr.release` raised INTERFACE_NOT_BUMPED ("already has interface '1' with a different
boundary"). Listing version 2 only adds `key` and `pin` to each boundary entry, and the facade
compared the stored v1 boundary with the fresh v2 one field for field.

The rule (decision model-0307): `derive.boundary_changed(previous, new)` compares only the fields
the previous listing's version carries, so an unchanged boundary is unchanged.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from stale_releases import OLD_BAR, cut_old, unit_id

from fransys_model.derive import baseline


class _Io(NamedTuple):
    X1_L1: Any
    X2_L2: Any


def _io(d: fr.Design) -> _Io:
    a1 = d.device("A1", "DEMO-IO-2X", interface=True)
    return _Io(a1.x1, a1.x2)


_FIRST = fr.unit(
    "demo-io", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
_SECOND = fr.unit(
    "demo-io", revision=2, interface_version=1, date="2026-02-01", text="again", by="AB"
)


def _build(unit_fn: Any) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(unit_fn(_io), "U1")
    return fr.build(d)


def test_an_unchanged_unit_released_over_a_listing_v1_does_not_bump_its_interface(
    tmp_path: Path,
) -> None:
    first = _build(_FIRST)
    folder = fr.release(first, tmp_path, unit="demo-io")
    old = baseline.listing(first.model, unit_id(first, "demo-io"), OLD_BAR)
    cut_old(folder, first, "demo-io", "0.19.6", old)
    fr.release(_build(_SECOND), tmp_path, unit="demo-io")
