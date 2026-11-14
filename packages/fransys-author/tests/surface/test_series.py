"""`series` and `parallel` build the wires the engine script builds, and fail by name."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, override

import pytest
from _wire_records import wire_records
from author_catalogue import _library, _part
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._pairing import End, Ends, SeriesBridge, SeriesElement
from series_parts import _poles, series_library

from fransys_model.elecdef import LinkKind
from fransys_model.vocab import Conductor, FunctionKind, PartCategory, WireFacet, WireRowHint

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

WIRE = ("BK", 2.5)


@pytest.fixture(scope="module")
def lib() -> Draft:
    """The series library plus a breaker whose main and aux are both one pole."""
    draft = series_library()
    extra = _library(draft, "test-series-aux")
    part = _part(
        draft, extra, manufacturer="TestCo", mpn="TEST-MCB-AUX",
        category=PartCategory.PROTECTION, letter="Q",
    )  # fmt: skip
    _poles(draft, part, "main", FunctionKind.PROTECTION, LinkKind.PROTECTIVE, [("1", "2")])
    _poles(draft, part, "aux", FunctionKind.CONTACT_NO, LinkKind.SWITCHED, [("13", "14")])
    return draft


def _pins(d: Design, tag: str, mpn: str, function: str, names: list[str]) -> list[Any]:
    fn = d._engine.item(mpn, tag=tag, name=tag).fn(function)
    return [fn[name] for name in names]


class _Source(SeriesElement):
    """A fake protocol element: `width` supply-like ends on the load side of a breaker."""

    def __init__(self, d: Design, width: int) -> None:
        self.ports = _pins(d, "Q0", "TEST-MCB-3P", "main", ["2", "4", "6"][:width])

    @override
    def _series_width(self) -> int:
        return len(self.ports)

    @override
    def _series_ends(self, design: Design, width: int | None) -> Ends:
        ends = tuple(End(port, None) for port in self.ports)
        return Ends(ends, ends)


class _Bridge(SeriesBridge):
    """A fake bridge: it records what it was handed."""

    def __init__(self) -> None:
        self.seen: list[Any] = []

    @override
    def _series_between(self, design: Design, before: Any, after: Any, series: str) -> None:
        self.seen.append((before, after))


def test_breaker_contactor_overload_motor_equal_the_engine_script(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    f1, m1 = d.device("F1", "TEST-OL-3P"), d.device("M1", "TEST-MOTOR-3P")
    d.series(q1.main, k1, f1, m1, wire=("BK", 2.5))

    twin = design(lib, place="C1")
    wiring = twin._engine.wiring(colour="BK", gauge="2.5")
    q, k = (twin._engine.item(m, tag=t, name=t) for t, m in (("Q1", "TEST-MCB-3P"), ("K1", "TEST-KM-3P")))
    f, m = (twin._engine.item(x, tag=t, name=t) for t, x in (("F1", "TEST-OL-3P"), ("M1", "TEST-MOTOR-3P")))
    for source, load in ((q.fn("main"), k.fn("main")), (k.fn("main"), f.fn("main"))):
        for a, b in zip("246", "135", strict=True):
            wiring(source[a], load[b])
    for a, b in zip("246", "UVW", strict=True):
        wiring(f.fn("main")[a], m.fn("load")[b])
    assert wire_records(d) == wire_records(twin)
    assert len(wire_records(d)) == 18


def test_the_wire_is_a_colour_and_mm2_tuple(lib: Draft) -> None:
    d = design(lib, place="C1")
    d.series(d.device("Q1", "TEST-MCB-3P").main, d.device("K1", "TEST-KM-3P"), wire=("BK", 2.5))
    assert wire_records(d)


def test_a_series_that_reaches_no_supply_writes_hinted_wires_and_no_facet(lib: Draft) -> None:
    """Each made hop is a conductor and a `WireRowHint` over the table in force, no `WireFacet`."""
    d = design(lib, place="C1")
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    d.series(q1.main, k1, wire=0.75)
    records = d.draft().records()
    hints = [r for r in records if isinstance(r, WireRowHint)]
    assert len([r for r in records if isinstance(r, Conductor)]) == len(hints) == 3
    assert not [r for r in records if isinstance(r, WireFacet)]
    assert {h.gauge_mm2 for h in hints} == {Decimal("0.75")}
    assert hints[0].rows["AC_L1"].colour == "BK"
    assert hints[0].rows["DC_SIGNAL"].colour == "BU"


def test_a_parallel_of_a_button_and_a_contactor_aux_in_a_one_pole_series(lib: Draft) -> None:
    d = design(lib, place="C1")
    s0, s1 = d.device("S0", "TEST-BTN-NC"), d.device("S1", "TEST-BTN-NO")
    k1 = d.device("K1", "TEST-KM-3P")
    d.series(s0.contact, d.parallel(s1, k1.aux), k1.coil, wire=WIRE)

    twin = design(lib, place="C1")
    wiring = twin._engine.wiring(colour="BK", gauge="2.5")
    t0, t1 = (twin._engine.item(m, tag=t, name=t) for t, m in (("S0", "TEST-BTN-NC"), ("S1", "TEST-BTN-NO")))
    tk = twin._engine.item("TEST-KM-3P", tag="K1", name="K1")
    out = t0.fn("contact")["22"]
    wiring(out, t1.fn("contact")["13"])
    wiring(out, tk.fn("aux")["13"])
    wiring(t1.fn("contact")["14"], tk.fn("coil")["A1"])
    wiring(tk.fn("aux")["14"], tk.fn("coil")["A1"])
    assert wire_records(d) == wire_records(twin)


def test_a_one_port_function_ends_a_series(lib: Draft) -> None:
    d = design(lib, place="C1")
    s1, a1 = d.device("S1", "TEST-BTN-NO"), d.device("A1", "TEST-PLC-CH")
    d.series(s1.contact, a1.channel, wire=WIRE)
    twin = design(lib, place="C1")
    t1 = twin._engine.item("TEST-BTN-NO", tag="S1", name="S1")
    ta = twin._engine.item("TEST-PLC-CH", tag="A1", name="A1")
    twin._engine.wiring(colour="BK", gauge="2.5")(t1.fn("contact")["14"], ta.fn("channel")["CH"])
    assert wire_records(d) == wire_records(twin)


def test_a_protocol_element_sets_the_width_and_a_device_takes_it(lib: Draft) -> None:
    d = design(lib, place="C1")
    d.series(_Source(d, 3), d.device("Q1", "TEST-MCB-3P"), wire=WIRE)
    assert len(wire_records(d)) == 6


def test_a_bridge_lands_between_its_neighbours_and_wires_nothing(lib: Draft) -> None:
    d = design(lib, place="C1")
    bridge = _Bridge()
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    main = q1.main
    d.series(main, bridge, k1, wire=WIRE)
    ((before, after),) = bridge.seen
    assert before[0] is main
    assert after[0] is k1
    assert [e.port.name for e in before[1].load] == ["2", "4", "6"]
    assert [e.port.name for e in after[1].line] == ["1", "3", "5"]
    assert not wire_records(d)


def test_a_bridge_needs_a_plain_element_on_each_side(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-MCB-3P")
    with pytest.raises(AuthorError, match="a cable sits between two elements"):
        d.series(q1.main, _Bridge(), wire=WIRE)


def test_three_poles_into_one_names_the_counts(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, s1 = d.device("Q1", "TEST-MCB-3P"), d.device("S1", "TEST-BTN-NO")
    with pytest.raises(
        AuthorError,
        match=r"Q1\.main leaves with 3 poles .* S1\.contact takes 1 pole .*d\.series",
    ):
        d.series(q1.main, s1.contact, wire=WIRE)


def test_two_functions_of_the_width_name_both(lib: Draft) -> None:
    d = design(lib, place="C1")
    s1, q1 = d.device("S1", "TEST-BTN-NO"), d.device("Q1", "TEST-MCB-AUX")
    with pytest.raises(AuthorError, match="Q1: aux and main both have poles, say which"):
        d.series(s1.contact, q1, wire=WIRE)


def test_a_device_without_poles_is_named(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k2 = d.device("Q1", "TEST-MCB-3P"), d.device("K2", "TEST-COIL")
    with pytest.raises(AuthorError, match=r"K2 has no pole pair: .*`side`.*d\.series"):
        d.series(q1.main, k2, wire=WIRE)


def test_a_function_without_poles_is_named(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k2 = d.device("Q1", "TEST-MCB-3P"), d.device("K2", "TEST-COIL")
    with pytest.raises(AuthorError, match=r"K2\.coil has no line/load pole pair.*k2\.coil\.pins"):
        d.series(q1.main, k2.coil, wire=WIRE)


def test_a_device_with_no_function_of_the_width_lists_what_it_has(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, s1 = d.device("Q1", "TEST-MCB-3P"), d.device("S1", "TEST-BTN-NO")
    with pytest.raises(
        AuthorError,
        match=r"S1 has no function of 3 poles; it has: contact \(1\)\. .*d\.series",
    ):
        d.series(q1.main, s1, wire=WIRE)
    with pytest.raises(
        AuthorError,
        match=(
            r"K1 has no function of 2 poles; it has: aux \(1\), coil \(1\), main \(3\)\. "
            r".*K1\.aux"
        ),
    ):
        d.series(_Source(d, 2), d.device("K1", "TEST-KM-3P"), wire=WIRE)


def test_a_pin_in_the_middle_of_a_series_must_match_the_width(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    with pytest.raises(AuthorError, match=r"leaves with 3 poles .* takes 1 pole"):
        d.series(q1.main, k1.main["1"], k1.main, wire=WIRE)
    assert not wire_records(d)


def test_a_series_without_a_width_names_what_sets_it(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    with pytest.raises(AuthorError, match=r"set no width: Q1, K1\. Name a supply.*d\.series\(pin, pin, \.\.\.\)"):
        d.series(q1, k1, wire=WIRE)


def test_a_series_or_parallel_needs_two_and_a_known_element(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-MCB-3P")
    with pytest.raises(AuthorError, match="at least 2 elements, got 1"):
        d.series(q1.main, wire=WIRE)
    with pytest.raises(AuthorError, match="at least 2 members, got 1"):
        d.parallel(q1.main)
    with pytest.raises(AuthorError, match=r"a series takes a device.*not int"):
        d.series(q1.main, 7, wire=WIRE)


def test_a_series_element_without_ends_or_a_bridge_without_between_cannot_be_made() -> None:
    class _NoEnds(SeriesElement):
        pass

    class _NoBetween(SeriesBridge):
        pass

    for broken, missing in ((_NoEnds, "_series_ends"), (_NoBetween, "_series_between")):
        make: Any = broken
        with pytest.raises(TypeError, match=missing):
            make()


def test_a_parallel_followed_by_a_parallel_is_a_star_from_the_first_member_of_the_earlier_group(lib: Draft) -> None:
    d = design(lib, place="C1")
    s0, a1, a2, b1, b2 = (d.device(t, "TEST-BTN-NO") for t in ("S0", "S1", "S2", "S3", "S4"))
    d.series(s0.contact, d.parallel(a1.contact, a2.contact), d.parallel(b1.contact, b2.contact), wire=WIRE)

    twin = design(lib, place="C1")
    t0, t1, t2, t3, t4 = (twin._engine.item("TEST-BTN-NO", tag=t, name=t).fn("contact") for t in ("S0", "S1", "S2", "S3", "S4"))
    wiring = twin._engine.wiring(colour="BK", gauge="2.5")
    wiring(t0["14"], t1["13"])
    wiring(t0["14"], t2["13"])
    wiring(t1["14"], t2["14"])
    wiring(t1["14"], t3["13"])
    wiring(t1["14"], t4["13"])
    ends = [{frozenset((r.a, r.b)) for r in wire_records(x) if isinstance(r, Conductor)} for x in (d, twin)]
    assert len(ends[0]) == 5
    assert ends[0] == ends[1]
