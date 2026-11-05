"""Field case: `fr.readability` of a container unit that titles its nested cabinet's pages.
The bug: fr.readability raised KeyError on a layout.page id, as leads were kept for pages the document does not print.
Fixed by layout-0260, the report holds each page once, by the run that drew it, and only a printed page has leads."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
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
    u.layout.profile(hide_unused_pins=True)
    with u.function("B", "Group"):
        psu = u.device("T1", "DEMO-PSU-24")
        lamps = [u.device(f"P{i}", "DEMO-LAMP-24") for i in range(5)]
        inputs = [u.device(f"D{i}", "DEMO-PLC-DI-2") for i in range(5)]
    u.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    u.dc_supply("S", psu)
    for lamp, di in zip(lamps, inputs, strict=True):
        u.series(psu.output["+"], lamp["1"], wire=WIRE)
        u.series(psu.output["+"], di.di_1["1"], wire=WIRE)
        u.series(psu.output["-"], lamp["2"], wire=WIRE)
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
    u.add(_cabinet, "U1")
    with u.function("A", "Own"):
        psu = u.device("T1", "DEMO-PSU-24")
        lamp = u.device("H1", "DEMO-LAMP-24")
    u.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    u.series(psu.output["+"], lamp["1"], wire=WIRE)
    u.series(psu.output["-"], lamp["2"], wire=WIRE)
    return _Out()


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_container, "C1")
    return fr.build(d, unit_document("demo-container"))


def test_readability_reports_a_container_titling_its_nested_cabinet(built: fr.BuildResult) -> None:
    report = fr.readability(built)
    assert report.pages
