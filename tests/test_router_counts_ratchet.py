"""The router ratchet of decision layout-0253 (ROUTE-METER, WP-R1 of STUDY-ROUTER-2026-10-14).

Each build below is one that exercised a retry or a crossing in the study's corpus. `metered()`
counts what the router did on it: edges that failed, edges drawn only with the soft rectangles open
(layout-0209) or a foreign exit cell open (layout-0223), wrap re-searches, crossings, bends, runs
along a foreign outline, U shapes and `_search` calls. A count may fall, never rise: lower
`CEILING` in the commit that makes it fall. Run `pytest -s` to print the counts.
"""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
lazy from collections import Counter

import pytest
from fransys_el import OPTIONS
from route_meter import metered

from fransys_layout.engines import lay_out_schematic
from fransys_model.kernel import freeze

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "tests/field_cases"
KEYS = (
    "route_failed",
    "draw_soft_open",
    "draw_exits_open",
    "wrap_search",
    "crossings",
    "bends",
    "along_outline",
    "uturns",
    "search_calls",
)
# Per build, one ceiling per count in the order of KEYS. Baselined on main after TALL-HELD
# (layout-0234, cd030eb02): the two harness builds took one more crossing and two more bends, one
# U shape fewer, from the changed placement; replicas crossings fell from 50 to 48.
# Re-baselined after merging main into TNR-SAME-PAGE (model-0220): a terminal wired to several
# devices is drawn as a copy at each pin, so each copy is one more short routed wire (one more
# `_search` call: relay_bank_8 +14, relay_bank_9 +16, relay_bank_10_house +9, cabinet +2) and the
# long wires to the one terminal are gone (bends fell 36 to 28, 54 to 42, 36 to 28, 20 to 12;
# cabinet U shapes 9 to 5, one wrap re-search to none). With the copies off the counts are main's.
CEILING: dict[str, tuple[int, ...]] = {
    "strip_to_plc": (0, 0, 2, 0, 2, 10, 0, 0, 7),
    "harness_overfull": (0, 1, 0, 0, 8, 31, 0, 8, 10),
    "harness_box_below": (0, 1, 0, 0, 8, 31, 0, 8, 14),
    "replicas": (0, 0, 0, 0, 48, 54, 0, 0, 26),
    "replicas_contactor": (0, 0, 0, 0, 57, 68, 0, 3, 30),
    "coils_to_channels": (0, 0, 0, 2, 12, 32, 0, 18, 34),
    "relay_bank_8": (0, 0, 0, 0, 12, 28, 0, 12, 80),
    "relay_bank_9": (0, 0, 0, 0, 22, 42, 0, 16, 90),
    "relay_bank_10_house": (0, 0, 0, 0, 18, 28, 0, 12, 50),
    # cabinet re-baselined: SAME-PAGE-BRANCH (layout-0224, c000e067c) turns a marker pair
    # into a routed wire
    "cabinet": (0, 0, 0, 0, 1, 12, 0, 5, 28),
    # layout-0258: the build the picture shows (hinted chains); its crossings count the core line
    # `W1.3` too (4 wire-over-wire, 1 wire over the core)
    # model-0220: the copies add 2 routed wires (search calls 17 to 19), both across `W1.3`
    # (crossings 5 to 7, core crossings 1 to 3); copies off, the counts are layout-0258's
    "cabinet_chained": (0, 0, 0, 0, 7, 6, 0, 2, 19),
}


def _load(path: Path, name: str) -> Any:
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def _field(stem: str) -> Any:
    return _load(FIELD / f"{stem}.py", f"{stem}_for_router_counts")


def _builds() -> Iterator[tuple[str, Callable[[], Any]]]:
    strip = _field("test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it")
    yield "strip_to_plc", strip._built
    harness = _field("test_a_harness_line_on_an_overfull_page_still_routes")
    yield "harness_overfull", lambda: harness._built(2, 0, 2, looms=False)
    yield "harness_box_below", lambda: harness._built(2, 0, 6, looms=False)
    replicas = _field("test_a_split_unit_group_page_holding_only_replicas")
    yield "replicas", replicas._built
    yield "replicas_contactor", replicas._built_ctr
    coils = _field("test_a_bank_of_coils_returned_to_channels_does_not_cross")
    yield "coils_to_channels", coils._built
    bank = _field("test_a_larger_module_only_adds_pages_to_a_bank_of_relays")
    yield "relay_bank_8", lambda: bank._built("3.0", 8)
    yield "relay_bank_9", lambda: bank._built("3.0", 9)
    yield "relay_bank_10_house", lambda: bank._built(None, 10)
    cabinet = _load(ROOT / "packages/fransys-layout/tests/layout_cabinet.py", "cabinet_for_router")
    yield (
        "cabinet",
        lambda: lay_out_schematic(freeze(cabinet.build_cabinet(discovery=True)), OPTIONS),
    )
    yield (
        "cabinet_chained",
        lambda: lay_out_schematic(freeze(cabinet.build_cabinet(discovery=False)), OPTIONS),
    )


@pytest.fixture(scope="module")
def counts() -> dict[str, Counter[str]]:
    """One metered build per name, shared by every test of the module (the builds take seconds)."""
    out: dict[str, Counter[str]] = {}
    for name, build in _builds():
        with metered() as one:
            build()
        out[name] = one
        print(name, {k: one[k] for k in KEYS})  # noqa: T201 -- the counts are the report
    return out


@pytest.mark.parametrize("key", KEYS)
def test_a_router_count_never_rises(counts: dict[str, Counter[str]], key: str) -> None:
    """Per build and per count the router does no more than the ceiling.

    # UNDO: stages/route.py, `route_crossing_penalty` read as 0 in `_search` (crossings rise)
    """
    at = KEYS.index(key)
    over = {n: (c[key], CEILING[n][at]) for n, c in counts.items() if c[key] > CEILING[n][at]}
    assert over == {}


def test_the_meter_sees_the_retries_and_the_crossings(counts: dict[str, Counter[str]]) -> None:
    """The ratchet measures something: the builds that need a retry or cross a wire show it."""
    assert counts["strip_to_plc"]["draw_exits_open"] > 0
    assert counts["harness_overfull"]["draw_soft_open"] > 0
    assert counts["coils_to_channels"]["wrap_search"] > 0
    assert counts["replicas"]["crossings"] > 0
    assert all(c["routes"] > 0 and c["route_failed"] == 0 for c in counts.values())


def test_the_cabinet_crossing_of_the_core_line_w1_3_is_counted(
    counts: dict[str, Counter[str]],
) -> None:
    """Layout-0258: a wire across the cable core line `W1.3` is one of the cabinet's crossings.

    # UNDO: lint/page_counts.py, `wire_crossings` reads `lines` as empty (the core crossing goes)
    """
    assert counts["cabinet_chained"]["core_crossings"] == 3
    assert counts["cabinet_chained"]["crossings"] == 7
