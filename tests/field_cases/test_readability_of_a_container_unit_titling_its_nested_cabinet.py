"""Field case: `fr.readability` of a container unit that titles its nested cabinet's pages.

The engineering shape: a container unit nests a cabinet unit with `d.add` and calls
`d.layout.page_title` on what `d.add` returned. The nested cabinet sets its own layout profile
(hidden unused pins, a narrow column gap, a wide row spacing); the container has none.

The document prints the container's set only. The top run still lays the nested cabinet's pages,
with the top profile, and they have other ids than the pages its own run draws.

The bug: `fr.readability` raised KeyError on a `layout.page` id. The top run's power leads were
kept for those unprinted pages; they got no row, so the stale-page rule never dropped them, and
the id is not in the spliced model.

The rule (decision layout-0260): the report holds each page once, by the run that drew it, with
that run's power leads, and only a printed page has leads.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU

WIRE = (BU, 0.5)


class _Out(NamedTuple):
    pass


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Cabinet",
)
def _cabinet(u: Any) -> _Out:
    u.layout.profile(hide_unused_pins=True, column_gap=4, row_spacing=400)
    with u.function("B", "Group"):
        psu = u.device("T1", "DEMO-PSU-24")
        lamps = [u.device(f"P{i}", "DEMO-LAMP-24") for i in range(5)]
        inputs = [u.device(f"D{i}", "DEMO-PLC-DI-2") for i in range(5)]
    u.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    u.dc_supply("S", psu)
    for lamp, di in zip(lamps, inputs, strict=True):
        u.detail.wire(psu.output["+"], lamp["1"], wire=WIRE)
        u.detail.wire(psu.output["+"], di.di_1["1"], wire=WIRE)
        u.detail.wire(psu.output["-"], lamp["2"], wire=WIRE)
    return _Out()


@fr.unit(
    "demo-container",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Container",
)
def _container(u: Any) -> _Out:
    cab = u.add(_cabinet, "U1")
    u.layout.page_title(cab, "Nested cabinet")
    with u.function("A", "Own"):
        psu = u.device("T1", "DEMO-PSU-24")
        lamp = u.device("H1", "DEMO-LAMP-24")
    u.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    u.detail.wire(psu.output["+"], lamp["1"], wire=WIRE)
    u.detail.wire(psu.output["-"], lamp["2"], wire=WIRE)
    return _Out()


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_container, "C1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Container\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=cover)
    )


def test_readability_reports_a_container_titling_its_nested_cabinet(built: fr.BuildResult) -> None:
    report = fr.readability(built)
    assert report.pages
