"""Cable drawing checks (spec step 3b, E3, E6).

It reads the rows the WireViz cable drawings are drawn from, `fr.derive.top_level_cables`, and
checks -W11 and -W21 against E3: four cores from the `-X3` strip to the motor, each core joining
the pump's terminal to the motor pin in E3's order (U to U1, V to V1, W to W1, PE to PE). The
cable and each core end carry the printed designation (`-W11`, `-X3:U:1`, `-M1:U1`); an end is
named by its product designation (`-U1-X3`, `+EXT-M1`). A strip end lists its terminals by their
bare `group:index` designation (`U:1`); the motor end lists its own port names. The expected
strings stay literals: computing them with `fr.derive.printed_designation` would test the
function against itself.

The can-fail proof (drop one core of -W11 in a scratch copy of `build.py`, confirm this module
fails, undo) is a manual verification done once with `Edit`, not a permanent test.
"""

import csv
from pathlib import Path

import fransys as fr
import pytest

# (cable designation, pump number, motor designation), from E3.
PUMP_CABLES = [("-W11", 1, "-M1"), ("-W21", 2, "-M2")]


def _cable(result: fr.BuildResult, designation: str) -> fr.derive.HarnessCable:
    found = [c for c in fr.derive.top_level_cables(result.model) if c.designation == designation]
    assert len(found) == 1, f"expected one top-level cable {designation}, got {len(found)}"
    return found[0]


@pytest.mark.parametrize(("designation", "pump", "motor"), PUMP_CABLES)
def test_motor_cable_ends(
    built: tuple[fr.BuildResult, Path, Path], designation: str, pump: int, motor: str
) -> None:
    """Two ends: the `-X3` strip with the pump's four terminals, and the motor's four pins."""
    result, _, _ = built
    cable = _cable(result, designation)
    assert len(cable.ends) == 2
    ends = {end.designation: end for end in cable.ends}
    assert set(ends) == {"-U1-X3", f"+EXT{motor}"}
    strip_pins = {pin.marking for pin in ends["-U1-X3"].pins}
    assert len(ends["-U1-X3"].pins) == 4
    assert strip_pins == {f"U:{pump}", f"V:{pump}", f"W:{pump}", f"PE:{pump}"}
    motor_pins = {pin.marking for pin in ends[f"+EXT{motor}"].pins}
    assert len(ends[f"+EXT{motor}"].pins) == 4
    assert motor_pins == {"PE", "U1", "V1", "W1"}


@pytest.mark.parametrize(("designation", "pump", "motor"), PUMP_CABLES)
def test_motor_cable_cores(
    built: tuple[fr.BuildResult, Path, Path], designation: str, pump: int, motor: str
) -> None:
    """Four cores, indices 1..4, each joining the `-X3` terminal to the motor pin (E3)."""
    result, _, _ = built
    cable = _cable(result, designation)
    assert cable.core_count == 4
    cores = sorted(cable.cores, key=lambda core: core.index)
    assert [core.index for core in cores] == [1, 2, 3, 4]
    # The ends are ordered by designation: `-Mn` sorts before `-U1-X3`.
    expected = [
        (1, f"{motor}:U1", f"-U1-X3:U:{pump}"),
        (2, f"{motor}:V1", f"-U1-X3:V:{pump}"),
        (3, f"{motor}:W1", f"-U1-X3:W:{pump}"),
        (4, f"{motor}:PE", f"-U1-X3:PE:{pump}"),
    ]
    assert [(c.index, c.end_a_designation, c.end_b_designation) for c in cores] == expected


def test_system_pdf_written(built: tuple[fr.BuildResult, Path, Path]) -> None:
    """The system document lands in `out/all/` as `EX-1-v1.2.pdf`."""
    _, out_dir, _ = built
    assert (out_dir / "all" / "EX-1-v1.2.pdf").is_file()


def test_cable_list_one_row_per_top_level_cable(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """`all/cables.csv`: -W1, -W11, -W21 and the harness cable, one row each, no unit column."""
    _, out_dir, _ = built
    with (out_dir / "all" / "EX-1-v1.2-cables.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["designation"] for row in rows] == ["-W1", "-W11", "-W21", "-W3-W1"]
    assert not any("unit" in column for column in rows[0])
