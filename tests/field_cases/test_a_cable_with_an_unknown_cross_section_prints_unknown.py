"""Field case: a fitted cable whose part states its cross-section as "unknown" (gauge_mm2 = "unknown").
The bug: the contract had no way to say it; a made-up number or a blank would print.
Fixed by R2540/R2541: the cable list prints the word unknown, and one GAUGE_UNKNOWN INFO names the part."""

import fransys as fr
import pytest
from fransys_reports import cables_csv

from fransys_model.derive import cable_list_rows


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """One two-core cable between two demo headers."""
    d = fr.design("demo_parts", "gauge_parts")
    d.location("L0", "Workshop")
    j1, j2 = (d.device(tag, "DEMO-CONN-4P", place="L0") for tag in ("X1", "X2"))
    cable = d.cable("W1", "GAUGE-CBL-2C", name="sensor", place="L0")
    cable.core(1, j1[1], j2[1])
    cable.core(2, j1[2], j2[2])
    return fr.build(d)


def test_the_build_has_no_error(built: fr.BuildResult) -> None:
    """A stated unknown is not an error."""
    assert [f.code for f in fr.check(built) if f.severity.name == "ERROR"] == []


def test_the_cable_list_shows_unknown(built: fr.BuildResult) -> None:
    """The row and the CSV cell print the word, never a blank or a number."""
    (row,) = cable_list_rows(built.model)
    assert row.cross_section == "unknown"
    assert ",unknown," in cables_csv(built.model)


def test_one_gauge_unknown_info_names_the_part(built: fr.BuildResult) -> None:
    """Exactly one INFO, naming the part."""
    found = [f for f in fr.check(built) if f.code == "GAUGE_UNKNOWN"]
    assert len(found) == 1
    assert found[0].severity.name == "INFO"
    assert "GAUGE-CBL-2C" in found[0].message
