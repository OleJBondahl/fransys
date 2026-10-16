"""Field case: an earth core goes to a PE end only; with none, too few cores is an error.

The engineering shape: a multi-pole load joined by a multi-core cable to another load. One core is
the earth core (GNYE). It lands on a PE port or a strip's PE terminal, never on a pole.

The bug (work order API-FRICTION-3 item 7): a motor with U V W and PE, fed through a four-core
cable from a three-pole breaker, must put the GNYE core on the PE port. With no PE end and more
poles than non-earth cores, the series is refused with an error that names the cable, both counts
and the fix (designer 2026-10-16, option (a): no positional fallback). Demo parts: DEMO-MOTOR-4KW,
DEMO-ISO-4P, DEMO-CBL-4G1.5. Decision author-0061 (API-FRICTION-3 item 7).
"""

import fransys as fr
import pytest
from fransys_author import AuthorError


def _no_pe_design() -> fr.Design:
    d = fr.design("demo_parts")
    q1 = d.device("Q1", "DEMO-ISO-4P")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    q2 = d.device("Q2", "DEMO-ISO-4P")
    d.series(q1.main, w1, q2.main)
    return d


def _pe_design() -> fr.Design:
    d = fr.design("demo_parts")
    q1 = d.device("Q1", "DEMO-MCB-3P")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(q1.element, w1, m1.motor)
    return d


def _cores(d: fr.Design) -> list[tuple[int, str, str, str]]:
    return [
        (r.core, r.colour, r.end_a, r.end_b) for r in fr.derive.core_list_rows(fr.build(d).model)
    ]


def test_with_no_pe_end_and_too_few_cores_the_series_is_refused() -> None:
    with pytest.raises(AuthorError) as raised:
        _no_pe_design()
    text = str(raised.value)
    assert "W1" in text
    assert "3 non-earth cores for 4 poles" in text
    assert "pick a cable with 4 non-earth cores" in text


def test_with_a_pe_end_the_earth_core_lands_on_that_pe_pin_only() -> None:
    assert _cores(_pe_design()) == [
        (1, "BN", "-M1:U", "-Q1:2"),
        (2, "BK", "-M1:V", "-Q1:4"),
        (3, "GY", "-M1:W", "-Q1:6"),
        (4, "GNYE", "-M1:PE", ""),
    ]


def test_with_a_pe_end_too_few_cores_says_free_cores_not_missing_pe() -> None:
    d = fr.design("demo_parts")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(d.device("Q1", "DEMO-MCB-3P").element, w1, d.device("M1", "DEMO-MOTOR-4KW").motor)
    q2 = d.device("Q2", "DEMO-MCB-3P")
    with pytest.raises(AuthorError, match=r"W1 has 0 free cores for 3 poles") as raised:
        d.series(q2.element, w1, d.device("M2", "DEMO-MOTOR-4KW").motor)
    assert "PE end" not in str(raised.value)
