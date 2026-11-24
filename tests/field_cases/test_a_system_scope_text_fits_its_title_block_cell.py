"""Field case: the system document's scope cell printed the Project's title, which the title cell already holds.
The bug (KI-1009): the scope text runs out of its title-block cell, cut with the ellipsis and raising TITLE_BLOCK_TEXT_OVERFLOW.
Fixed (R3743): a document with no location and no unit prints an empty scope, as the title cell holds the title."""

import fransys as fr
import pytest
from _model_build_cover import system_document


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    d.project(
        title="Water treatment plant extension, boiler house and pump station control system",
        number="R-1",
        customer="Example Co",
        revision=1,
        author="XX",
    )
    d.revision(1, date="2026-10-26", text="First issue", created="XX")
    with d.function("SUP", "Incoming supply"):
        run = d.terminal_strip("X0", "DEMO-TB-2.5", external=True).run("L1", 2)
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.series(run[1], lamp["1"], wire=("BK", 0.5))
        d.series(run[2], lamp["2"], wire=("BK", 0.5))
    return fr.build(d, system_document())


def test_no_scope_text_overflows_its_cell(built: fr.BuildResult) -> None:
    assert not [f for f in fr.check(built) if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"]
