"""Field case: a four-core cable whose green-yellow core reaches no pin, because neither end offers PE.
The bug: the core printed "4 GNYE spare", unterminated, under a heading that says "including a protective earth core".
Fixed by model-0484, PE_CORE_WITHOUT_SERIES refuses it and names the PE terminal, d.earth and the series to the PE pin."""

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK, GNYE

CODE = "PE_CORE_WITHOUT_SERIES"


def test_a_gnye_core_with_no_series_is_an_error_with_the_exact_fix() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(dc.plus, x1, w1, d.device("H1", "DEMO-LAMP-24").lamp, dc.minus, wire=(BK, 0.75))
    result = fr.build(d)
    expect_codes(result, CODE)
    (found,) = [f for f in result.findings if f.code == CODE]
    assert found.severity.name == "ERROR"
    assert found.fix.endswith(
        'Write: pe = x1.run("PE", 2, bridged=True); w1.core(GNYE, m1.motor["PE"], pe[1]); '
        'd.earth(m1.motor["PE"], pe[1]); d.series(x1[1:4], w1, m1.motor)'
    )


def test_the_form_the_fix_text_spells_is_clean_and_the_core_lands_on_the_pe_pin() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
    pe = x1.run("PE", 2, bridged=True)
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    w1.core(GNYE, m1.motor["PE"], pe[1])
    d.earth(m1.motor["PE"], pe[1])
    d.series(x1[1:4], w1, m1.motor)
    result = fr.build(d)
    assert [f for f in result.findings if f.code == CODE] == []
    assert [f.code for f in result.findings if f.severity.name == "ERROR"] == []


def test_an_earthed_motor_pe_pin_with_the_gnye_core_never_named_is_an_error() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    d.earth(d.device("M1", "DEMO-MOTOR-4KW").motor["PE"])
    d.series(x1[1:4], d.cable("W1", "DEMO-CBL-4G1.5"), d.device("K1", "DEMO-CTR-3P-24").main)
    expect_codes(fr.build(d), CODE)


def test_a_gnye_core_parked_on_a_pin_off_the_pe_net_is_an_error() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    w1.spare(GNYE, at=x1[8])
    d.series(x1[1:4], w1, d.device("M1", "DEMO-MOTOR-4KW").motor)
    expect_codes(fr.build(d), CODE)
