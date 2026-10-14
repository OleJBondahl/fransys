"""SERIES-GAPS S7 refusals (A6): a changeover whole, and `.no` on a function that is not one."""

import fransys as fr
import pytest


def test_a_changeover_passed_whole_raises_and_names_its_two_throws() -> None:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-CTR-3P-24")
    with pytest.raises(
        fr.AuthorError, match=r"a changeover is two throws: use K1.co_1.no or K1.co_1.nc"
    ):
        d.series(dc.plus, k1.co_1, k2.coil, dc.minus, wire=0.75)


def test_a_throw_on_a_function_that_is_not_a_changeover_raises_and_names_its_kind() -> None:
    d = fr.design("demo_parts")
    k2 = d.device("K2", "DEMO-CTR-3P-24")
    with pytest.raises(fr.AuthorError, match=r"K2.coil is a coil function, not a changeover"):
        _ = k2.coil.no


def test_two_series_through_both_throws_wire_the_common_once() -> None:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    k2, k3 = d.device("K2", "DEMO-CTR-3P-24"), d.device("K3", "DEMO-CTR-3P-24")
    d.series(dc.plus, k1.co_1.no, k2.coil, dc.minus, wire=0.75)
    d.series(dc.plus, k1.co_1.nc, k3.coil, dc.minus, wire=0.75)
    ends = [{r.from_, r.to} for r in fr.derive.wire_rows(fr.build(d).model)]
    assert sum("-K1:11" in pair for pair in ends) == 1
    assert {"-K1:12", "-K3:A1"} in ends


def test_a_throw_is_a_missing_attribute_on_a_coil() -> None:
    d = fr.design("demo_parts")
    assert not hasattr(d.device("K2", "DEMO-CTR-3P-24").coil, "no")
