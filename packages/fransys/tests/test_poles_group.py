"""API-CLARITY C6.4: `d.poles` groups one-pole contacts of one device (author-0046, layout-0227)."""

from types import SimpleNamespace

import fransys as fr
import pytest

from fransys_layout.engines.schematic.read import reading
from fransys_layout.engines.schematic.read.pole_groups import gang_specs
from fransys_model.derive.indexes import build_indexes
from fransys_model.layout import PoleGroup, layout_of
from fransys_model.vocab.tables import functions


def _ends(d) -> set[frozenset[str]]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def _three_phase(d):
    xa = d.terminal_strip("XA", "DEMO-TB-2.5")
    a = d.ac_supply("A", "230", xa[1], xa[2], xa[3])
    return a, d.device("QA", "DEMO-MCB-3P"), d.device("M1", "DEMO-MOTOR-4KW")


def test_a_changeover_group_with_no_selector_takes_the_line_at_its_commons() -> None:
    d = fr.design("demo_parts")
    a, qa, m1 = _three_phase(d)
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    d.series(a, qa.element, d.poles(k1.co_1, k1.co_2, k1.co_3).no, m1, wire=2.5)
    ends = _ends(d)
    for pole, line, motor in ((1, "2", "U"), (2, "4", "V"), (3, "6", "W")):
        assert frozenset((f"-QA:{line}", f"-K1:{pole}1")) in ends
        assert frozenset((f"-K1:{pole}4", f"-M1:{motor}")) in ends


def test_a_make_group_stands_in_a_series_as_its_members_do() -> None:
    def build(*, grouped: bool) -> set[frozenset[str]]:
        d = fr.design("demo_parts")
        dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
        k1, k2 = d.device("K1", "DEMO-CTR-3P-24"), d.device("K2", "DEMO-CTR-3P-24")
        d.series(dc.plus, d.poles(k1.aux) if grouped else k1.aux, k2.coil, dc.minus, wire=0.75)
        return _ends(d)

    assert build(grouped=True) == build(grouped=False)


def test_the_group_is_one_record_in_the_authors_pole_order() -> None:
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    d.poles(k1.co_3, k1.co_1, selector=True)
    model = fr.build(d).model
    (group,) = layout_of(model, PoleGroup).values()
    assert [functions(model)[f].key[-1] for f in group.functions] == ["co_3", "co_1"]
    assert group.selector


def _refusal(make) -> str:
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    k2 = d.device("K2", "DEMO-CTR-3P-NC")
    with pytest.raises(fr.AuthorError) as raised:
        make(SimpleNamespace(d=d, k1=k1, k2=k2))
    return str(raised.value)


@pytest.mark.parametrize(
    ("make", "text"),
    [
        (lambda x: x.d.poles(), "d.poles groups one function or more"),
        (lambda x: x.d.poles(x.k1), "not Device"),
        (lambda x: x.d.poles(x.k1.coil), "K1.coil is a coil function"),
        (lambda x: x.d.poles(x.k1.co_1, x.k2.aux), "K2.aux is not a function of K1"),
        (lambda x: x.d.poles(x.k2.aux, x.k2.aux_nc), "K2.aux_nc is a contact_nc function, not"),
        (lambda x: x.d.poles(x.k2.main), "K2.main has 3 poles"),
        (lambda x: x.d.poles(x.k1.co_1, x.k1.co_1), "K1.co_1 is in a pole group already"),
        (
            lambda x: (x.d.poles(x.k1.co_1), x.d.poles(x.k1.co_2, x.k1.co_1)),
            "K1.co_1 is in a pole group already",
        ),
        (
            lambda x: x.d.poles(x.k2.aux, selector=True),
            "selector=True turns changeover throws; K2.aux is a contact_no function",
        ),
        (lambda x: x.d.poles(x.k2.aux).no, "a group of contact_no functions has no throws"),
        (
            lambda x: x.d.series(x.k2.coil, x.d.poles(x.k1.co_1), x.k2.coil),
            "a changeover group is two throws",
        ),
    ],
)
def test_a_group_that_cannot_stand_raises_naming_it(make, text: str) -> None:
    assert text in _refusal(make)


def test_a_relay_selector_group_reads_as_the_three_pole_selector_part() -> None:
    """layout-0227: three grouped one-pole changeovers read as DEMO-SEL-3P-24's one function."""
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    d.device("Q1", "DEMO-SEL-3P-24")
    d.poles(k1.co_1, k1.co_2, k1.co_3, selector=True)
    model = fr.build(d).model
    specs, leader = gang_specs(model, reading.drawn_functions(model, build_indexes(model)))
    shape = {
        spec.key[-3]: (
            spec.poles,
            spec.pole_pairs,
            [(p.name, p.throw, p.pole, p.line, p.order) for p in spec.ports],
        )
        for spec in specs
        if spec.kind == "contact_co" and spec.key[-1] in {"co", "co_1"}
    }
    assert shape["K1"] == shape["Q1"]
    assert len(leader) == 2
