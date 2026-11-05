"""Field case: three relay coils whose A1 terminals share one net with one digital input channel.
The bug: on main K2 and K3 got PLC_BINDING_WIRING_MISMATCH, each bound to the channel K1 also holds, and no contest was raised.
Fixed by model-0211 (amended, PLC-CONTESTED, designer 2026-10-14), requests picking one wired channel raise PLC_CHANNEL_CONTESTED."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys.colours import BK
from fransys.pipeline import BuildFailedError

if TYPE_CHECKING:
    from pathlib import Path

ALLOWED_CODES = {"ITEM_WITHOUT_PART"}  # the demo coils carry no part number


def test_three_coil_requests_on_one_channel_are_contested() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    for n in (1, 2, 3):
        coil = d.device(f"K{n}", "DEMO-CO-4P-24")
        d.series(coil.coil["A1"], di.di_1["1"], wire=(BK, 1.0))
        coil.coil.plc(fr.DI, f"K{n} coil")
    d.device("K4", "DEMO-CO-4P-24").coil.plc(fr.DI, "K4 free")
    build = fr.build(d)
    expect_codes(build, "FUNCTION_HALF_CONNECTED", "PLC_CHANNEL_CONTESTED")
    found = [f for f in fr.check(build) if f.code not in ALLOWED_CODES]
    assert len(found) == 4  # three coils wired at A1 only, one contest
    findings = [f for f in found if f.code == "PLC_CHANNEL_CONTESTED"]
    assert findings[0].severity is fr.Severity.ERROR
    assert all(f"-K{n}" in findings[0].message for n in (1, 2, 3))
    assert "-A1:1" in findings[0].message
    rows = fr.derive.plc_channel_rows(build.model)
    assert {row.pin: row.signal_name for row in rows if row.signal_name} == {"-A1:2": "K4 free"}


def test_one_request_among_three_coils_on_a_net_binds_the_wired_channel_without_a_finding() -> None:
    """True model of the legacy circuit: only K1 asks; K2 and K3 share the net but ask for nothing.

    The wired channel is the second one, so a bind by the free queue (first channel) would differ.
    """
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    coils = [d.device(f"K{n}", "DEMO-CO-4P-24") for n in (1, 2, 3)]
    for coil in coils:
        d.series(coil.coil["A1"], di.di_2["2"], wire=(BK, 1.0))
    coils[0].coil.plc(fr.DI, "Contactors closed")
    build = fr.build(d)
    expect_codes(build, "FUNCTION_HALF_CONNECTED")
    findings = [f.code for f in fr.check(build) if f.code not in ALLOWED_CODES]
    assert findings == ["FUNCTION_HALF_CONNECTED"] * 3  # each coil is wired at A1 only; no PLC finding
    named = {row.pin: row.signal_name for row in fr.derive.plc_channel_rows(build.model)}
    assert named["-A1:2"] == "Contactors closed"


def test_a_coil_wired_at_one_port_makes_write_refuse_and_write_nothing(tmp_path: Path) -> None:
    """FUNCTION_HALF_CONNECTED is an ERROR (model-0224, R1608): `fr.write` raises BuildFailedError, the folder stays empty."""
    d = fr.design("demo_parts")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=d.rack("U1"))
    d.series(d.device("K1", "DEMO-CO-4P-24").coil["A1"], di.di_1["1"], wire=(BK, 1.0))
    result = fr.build(d)
    expect_codes(result, "FUNCTION_HALF_CONNECTED")
    half = [f for f in result.findings if f.code == "FUNCTION_HALF_CONNECTED"]
    assert [f.severity for f in half] == [fr.Severity.ERROR]
    with pytest.raises(BuildFailedError):
        fr.write(result, tmp_path)
    assert list(tmp_path.iterdir()) == []
