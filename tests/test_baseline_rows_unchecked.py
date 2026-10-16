"""A baseline cut before 0.18.2 holds contact-block rows today's numbering cannot print (LS3).

`fr.verify` leaves out only the rows the holder rule governs and compares the rest under the
stored rules: all equal gives one INFO naming the count, one real change is still an ERROR.
"""

import dataclasses
from typing import Any
lazy from pathlib import Path

import fransys as fr
from stale_releases import build_plant, cut_old, old_listing, release_all


def _codes(findings: Any) -> list[tuple[str, str]]:
    return [(f.code, f.severity.name) for f in findings]


def test_left_out_rows_are_one_info_naming_the_release_and_the_count(tmp_path: Path) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    cut_old(folders["lg-cabinet"], result, "lg-cabinet", "0.18.1")
    findings = fr.verify(result, tmp_path)
    assert _codes(findings) == [("BASELINE_ROWS_UNCHECKED", "INFO")]
    message = findings[0].message
    assert "lg-cabinet 1.1" in message
    assert "3 rows" in message
    assert "fransys 0.18.1" in message
    assert "0.18.2" in message


def test_a_real_change_beside_the_left_out_rows_is_baseline_differs(tmp_path: Path) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    listing = old_listing(result, "lg-cabinet")
    rows = tuple(
        dataclasses.replace(c, colour="BU") if c.a == "-M1:PE" else c for c in listing.conductors
    )
    changed = dataclasses.replace(listing, conductors=rows)
    cut_old(folders["lg-cabinet"], result, "lg-cabinet", "0.18.1", changed)
    findings = fr.verify(result, tmp_path)
    assert _codes(findings) == [("BASELINE_DIFFERS", "ERROR")]
    assert findings[0].message.endswith("in: conductors")
