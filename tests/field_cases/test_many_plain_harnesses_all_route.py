"""Field case: three plain harnesses on one harness drawing, each a cable between two plugs, one
location per harness, both plugs of each a boundary port of the unit, no hints and no groups.

The bug: core 1 of the third harness gets `ROUTE_FAILED` and `CONNECTION_NOT_DRAWN`, and its wire
is missing from the drawing. Two harnesses never fail; the unit title "Demo" fails and "D" does
not, so the result moves with tiny layout-input changes (measured 2026-10-02). A consumer drawing
of 38 such harnesses lost core 1 of 9 of them.

Found by a consumer, reproduced 2026-10-02. The cause: the outline title of the unit's black box
(`unit_outlines`) was placed above the leftmost plug over its port's first outward step whenever
the title was wide enough to reach the port, and the router closes that step to every net but the
port's own. Fixed by layout-0088 (amended): the title keeps clear of every port's first step.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_BAD_CODES = {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}


def _build(title: str, count: int, cover_dir: Path) -> fr.BuildResult:
    """A unit of `count` plain harnesses (a 2-core cable between two plugs, pin i to pin i)."""

    @fr.unit(
        "demo",
        revision=1,
        interface_version=1,
        title=title,
        number="D-1",
        date="2026-10-02",
        text="First issue",
        by="XX",
    )
    def harnesses(u: fr.Design) -> _Open:
        for n in range(1, count + 1):
            u.location(f"L{n}", f"Loc {n}")
            near = u.device(None, _PLUG, name=f"P1_{n}", place=f"L{n}", interface=True)
            far = u.device(None, _PLUG, name=f"P2_{n}", place=f"L{n}", interface=True)
            cable = u.cable(f"W{n}", _CABLE, length_m=3, place=f"L{n}")
            for pin in (1, 2):
                cable.core(pin, near[pin], far[pin])
        return _Open()

    d = fr.design("demo_parts")
    d.add(harnesses, "DEMO")
    cover = cover_dir / "cover.md"
    cover.write_text("# Harnesses\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.HARNESS_DRAWING, "demo", cover=cover)
    return fr.build(d, doc)


@pytest.fixture(scope="module", params=["Demo", "D"])
def built(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> fr.BuildResult:
    return _build(request.param, 3, tmp_path_factory.mktemp("harnesses"))


def test_three_plain_harnesses_route_every_core(built: fr.BuildResult) -> None:
    """The wide title "Demo" reaches the first port's exit; the one-letter "D" never did."""
    assert {f.code for f in fr.check(built) if f.code in _BAD_CODES} == set()
