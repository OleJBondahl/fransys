"""Field case: a 1P+N breaker with its phase pole on a fed rail and its neutral pole on another net.

The engineering shape: a main switch feeds a bridged L1 rail. Two motor branches (a three-pole
breaker, a contactor, a strip) hang on the rail, and so does a one-device 1P+N control breaker:
its phase pole on the rail, its neutral pole on the supply neutral, both poles then to a supply.

The bug: the two poles of the control breaker are dealt as through elements of two different fans.
The phase pole was dealt into the first branch's lane, on top of that breaker's own pole, and the
neutral pole took a column of its own, so one symbol stood in two columns, was drawn twice on
different pages and lost the branch breaker's pole. The build raised SchemaError "the records put
name one id twice". The rule (BUNDLE, R283): a through element whose symbol has an element outside
its fan takes its symbol's own column, so one symbol stands in one column, and a symbol in two
columns is a named error, never a silent pick.
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BK, BN, BU, GY

WIRE = 1.5
sys.path.insert(0, str(Path(__file__).parent / "data"))  # the one-device 1P+N breaker


def _cover() -> Path:
    path = Path(tempfile.mkdtemp()) / "cover.md"
    path.write_text("# Rail\n", encoding="utf-8")
    return path


def _design() -> tuple[fr.Design, fr.Draft]:
    d = fr.design("demo_parts", "breaker_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Rail", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    with d.function("INC", "Incomer"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
        d.earth(x1.run("PE", 1)[1])
        d.ac_supply("400V", 230, x1[1], x1[2], x1[3], n=x1[4])
        q1 = d.device("Q1", "DEMO-ISO-4P")
        for terminal, pin, colour in ((1, "1", BN), (2, "3", BK), (3, "5", GY)):
            d.detail.wire(x1[terminal], q1.main[pin], wire=(colour, 2.5))
        x01 = d.terminal_strip("X01", "DEMO-TB-2.5", 12)
        rails = [x01.run(name, 4, bridged=True) for name in ("L1", "L2", "L3")]
        for rail, pin, colour in zip(rails, ("2", "4", "6"), (BN, BK, GY), strict=True):
            d.detail.wire(q1.main[pin], rail[1], wire=(colour, 2.5))
    with d.function("CTL", "Control supply"):
        f01, t1 = d.device("F01", "DEMO-MCB-1PN"), d.device("T01", "DEMO-PSU-24")
        d.detail.wire(rails[0][2], f01.pole["1"], wire=(BN, WIRE))
        d.detail.wire(x1[4], f01.pole["3"], wire=(BU, WIRE))
        d.detail.wire(f01.pole["2"], t1.input["L"], wire=(BN, WIRE))
        d.detail.wire(f01.pole["4"], t1.input["N"], wire=(BU, WIRE))
        d.dc_supply("24VDC", t1)
    with d.function("PUMPS", "Pumps"):
        for k in (1, 2):
            f, q = d.device(f"F{k}1", "DEMO-MCB-3P"), d.device(f"Q{k}1", "DEMO-CTR-3P-NC")
            xm = d.terminal_strip(f"XM{k}", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5")
            for i, colour in enumerate((BN, BK, GY)):
                d.detail.wire(rails[i][2 + k], f.element[("1", "3", "5")[i]], wire=(colour, WIRE))
                d.detail.wire(
                    f.element[("2", "4", "6")[i]], q.main[("1", "3", "5")[i]], wire=(colour, WIRE)
                )
                d.detail.wire(q.main[("2", "4", "6")[i]], xm[i + 1], wire=(colour, WIRE))
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=_cover())


def test_the_build_has_no_error_finding() -> None:
    result = fr.build(*_design())
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
