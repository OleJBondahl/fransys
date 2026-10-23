"""EL-5 template facts: one function per rule of `derive/facts/part.py`, each planted.

Every part is invented. Can-fail probe: swap two pins in `poles_of_template` and the pairing,
changeover and breaker tests fail; drop the parity branch of `pole_side` and the side tests fail.
"""

import itertools
from decimal import Decimal

import pytest
from examples import relay_part_bundle

from fransys_model.derive import (
    channel_signal,
    conductor_of,
    contact_kind_of,
    implied_rest,
    is_contact_kind,
    pole_count,
    pole_pin_names,
    pole_side,
    poles_of_template,
    throws_of,
)
from fransys_model.derive.facts.part_poles import unlinked_poles
from fransys_model.kernel import Id
from fransys_model.vocab import CONDUCTOR_MARKS, THROWS, effective_rating
from fransys_model.vocab.enums import (
    ConductorMark,
    FunctionKind,
    LinkKind,
    PoleSide,
    PortRole,
    SignalType,
)
from fransys_model.vocab.facets import PlcChannelFacet
from fransys_model.vocab.ratings import Rating
from fransys_model.vocab.roles_types import complete
from fransys_model.vocab.templates import InternalLink, PortTemplate
lazy from fransys_model.vocab.markings import Pole

_COUNTER = itertools.count(1)
_FUNCTION = Id(kind="function_template", value="1" * 32)


def _pin(
    name: str,
    *,
    role: PortRole = PortRole.GENERIC,
    side: PoleSide | None = None,
    mark: ConductorMark | None = None,
) -> PortTemplate:
    return PortTemplate(
        id=Id(kind="port_template", value=f"{next(_COUNTER):032d}"),
        key=("t", "fn", "port", name),
        function=_FUNCTION,
        name=name,
        role=role,
        marking=name,
        pole_side=side,
        conductor_mark=mark,
    )


def _link(a: PortTemplate, b: PortTemplate, kind: LinkKind = LinkKind.SWITCHED) -> InternalLink:
    return InternalLink(
        id=Id(kind="internal_link", value=f"{next(_COUNTER):032d}"),
        key=("t", "fn", "link", a.name, b.name),
        a=a.id,
        b=b.id,
        kind=kind,
    )


def _names(poles) -> list[tuple[str, ...]]:
    return [tuple(p.name for p in pole.ends) for pole in poles]


def test_unlinked_pins_pair_in_port_order_key_order() -> None:
    """Pins given 10, 2, 9, 1 pair 1/2 and 9/10: marking order, pairs of two."""
    poles = unlinked_poles([_pin("10"), _pin("2"), _pin("9"), _pin("1")])
    assert _names(poles) == [("1", "2"), ("9", "10")]


def test_three_pins_and_no_pole_link_pair_the_first_two_and_keep_the_third() -> None:
    """A part with pins 3, 1, 2 and no link: (1, 2) then the odd pin 3 alone, not dropped."""
    pins = [_pin("3"), _pin("1"), _pin("2")]
    poles = poles_of_template(FunctionKind.GENERIC, pins, [])
    assert _names(poles) == [("1", "2"), ("3", "3")]


def test_the_fallback_leaves_an_earth_pin_out() -> None:
    """A PE pin is no pole pin: pins 1, 2 and a PE pin give one pole."""
    pins = [_pin("1"), _pin("2"), _pin("PE", role=PortRole.PE)]
    assert _names(poles_of_template(FunctionKind.GENERIC, pins, [])) == [("1", "2")]


def test_a_two_pole_breaker_gives_its_links_in_marking_order() -> None:
    """Links 3-4 then 1-2 give poles 1/2 and 3/4, line side first by the stated sides."""
    p1, p2, p3, p4 = (
        _pin(n, side=s) for n, s in zip("1234", [PoleSide.LINE, PoleSide.LOAD] * 2, strict=True)
    )
    links = [_link(p3, p4), _link(p1, p2)]
    poles = poles_of_template(FunctionKind.PROTECTION, [p4, p3, p2, p1], links)
    assert _names(poles) == [("1", "2"), ("3", "4")]
    assert [pole.ends[0].name for pole in poles if pole.line is pole.ends[0]] == ["1", "3"]
    assert pole_count(poles) == 2


def test_a_changeover_is_one_pole_by_count_and_two_links_by_poles() -> None:
    """`11-12` and `11-14` share `11`: two switched links, one connected pole."""
    c, b, m = (
        _pin(n, role=r)
        for n, r in [("11", PortRole.COMMON), ("12", PortRole.BREAK), ("14", PortRole.MAKE)]
    )
    links = [_link(c, b), _link(c, m)]
    poles = poles_of_template(FunctionKind.CONTACT_CO, [c, b, m], links)
    assert len(poles) == 2
    assert pole_count(poles) == 1
    pins = {t.id: t for t in (c, b, m)}
    throws = throws_of(links, pins)
    assert [(pins[t.common].name, t.role, pins[t.throw].name) for t in throws] == [
        ("11", PortRole.BREAK, "12"),
        ("11", PortRole.MAKE, "14"),
    ]
    assert [t.closed_at_rest for t in throws] == [True, False]


def test_sideless_gives_no_pairs_from_the_fallback() -> None:
    """Three unmarked pins with `sideless`: no poles; without it, the pairing fallback."""
    pins = [_pin("1"), _pin("2"), _pin("3")]
    assert poles_of_template(FunctionKind.GENERIC, pins, [], sideless=True) == ()
    assert len(poles_of_template(FunctionKind.GENERIC, pins, [])) == 2


def test_sideless_keeps_a_lone_pin_and_a_line_load_pair() -> None:
    """The old author rule: one pin is a pole; two pins with a line side are that pole."""
    lone = [_pin("x")]
    assert _names(poles_of_template(FunctionKind.GENERIC, lone, [], sideless=True)) == [("x", "x")]
    pair = [_pin("b"), _pin("a", side=PoleSide.LINE)]
    (pole,) = poles_of_template(FunctionKind.GENERIC, pair, [], sideless=True)
    assert (pole.ends[0].name, pole.ends[1].name) == ("a", "b")
    assert pole.line is pole.ends[0]
    no_side = [_pin("a"), _pin("b")]
    assert poles_of_template(FunctionKind.GENERIC, no_side, [], sideless=True) == ()


def test_marked_pins_of_a_sideless_part_are_one_pole_each() -> None:
    """Pins U, V, W carrying L1, L2, L3 and no link: sideless gives three one-pin poles."""
    marks = (ConductorMark.L1, ConductorMark.L2, ConductorMark.L3)
    pins = [_pin(n, mark=m) for n, m in zip("WVU", reversed(marks), strict=True)]
    poles = poles_of_template(FunctionKind.LOAD, pins, [], sideless=True)
    assert _names(poles) == [("U", "U"), ("V", "V"), ("W", "W")]
    assert pole_count(poles) == 3


def test_marked_pins_of_a_load_are_one_pin_poles() -> None:
    """A load's pins U, V, W name conductors and have no side: three one-pin poles (NS-2b)."""
    marks = (ConductorMark.L1, ConductorMark.L2, ConductorMark.L3)
    pins = [_pin(n, mark=m) for n, m in zip("WVU", reversed(marks), strict=True)]
    poles = poles_of_template(FunctionKind.LOAD, pins, [])
    assert _names(poles) == [("U", "U"), ("V", "V"), ("W", "W")]


def test_pole_side_stated_wins_then_parity_then_coil() -> None:
    """A stated side wins; a numeric marking on a pole pin is line when odd, load when even."""
    on_pole = {"1", "2", "x"}
    assert pole_side(_pin("1"), FunctionKind.CONTACT_NO, on_pole) is PoleSide.LINE
    assert pole_side(_pin("2"), FunctionKind.CONTACT_NO, on_pole) is PoleSide.LOAD
    assert (
        pole_side(_pin("2", side=PoleSide.LINE), FunctionKind.CONTACT_NO, on_pole) is PoleSide.LINE
    )
    assert pole_side(_pin("3"), FunctionKind.CONTACT_NO, on_pole) is None
    assert pole_side(_pin("x"), FunctionKind.CONTACT_NO, on_pole) is None
    assert pole_side(_pin("A1"), FunctionKind.COIL, set()) is PoleSide.LINE
    assert pole_side(_pin("A2"), FunctionKind.COIL, set()) is PoleSide.LOAD


def test_contact_kind_of_names_the_plain_contacts() -> None:
    """NO, NC and CO give their words; a switch and a non-contact give none."""
    assert contact_kind_of(FunctionKind.CONTACT_NO) == "no"
    assert contact_kind_of(FunctionKind.CONTACT_NC) == "nc"
    assert contact_kind_of(FunctionKind.CONTACT_CO) == "co"
    assert contact_kind_of(FunctionKind.SWITCH) is None
    assert contact_kind_of(FunctionKind.COIL) is None


def test_the_throw_table_is_complete_and_names_the_throws() -> None:
    """Every role has a row; BREAK is `nc` closed at rest, MAKE is `no`, COMMON neither."""
    assert set(THROWS) == set(PortRole)
    assert (THROWS[PortRole.BREAK].word, THROWS[PortRole.BREAK].closed_at_rest) == ("nc", True)
    assert (THROWS[PortRole.MAKE].word, THROWS[PortRole.MAKE].closed_at_rest) == ("no", False)
    assert THROWS[PortRole.COMMON].common
    assert [r for r in PortRole if THROWS[r].throw] == [PortRole.BREAK, PortRole.MAKE]
    short = {role: row for role, row in THROWS.items() if role is not PortRole.MAKE}
    with pytest.raises(RuntimeError, match="MAKE"):
        complete(short, PortRole)


def test_the_conductor_table_copies_the_parts_markings() -> None:
    """The DC signs and the motor ends map as the parts lint's table did; each mark is reachable."""
    assert CONDUCTOR_MARKS["+"] is ConductorMark.L_PLUS
    assert CONDUCTOR_MARKS["W1"] is ConductorMark.L3
    assert set(CONDUCTOR_MARKS.values()) == set(ConductorMark)
    assert len(CONDUCTOR_MARKS) == len(ConductorMark) + 8


def test_effective_rating_is_the_templates_whole_else_the_parts() -> None:
    """A template rating replaces the part's whole; none falls back on the part's."""
    own, part = Rating(voltage_ac_v=Decimal(1)), Rating(voltage_dc_v=Decimal(2))
    assert effective_rating(own, part) is own
    assert effective_rating(None, part) is part
    assert effective_rating(None, None) is None


def test_channel_signal_reads_the_facet_or_none() -> None:
    """A channel template gives its facet's signal; any other template gives none."""
    template = Id(kind="function_template", value="2" * 32)
    facet = PlcChannelFacet(
        id=Id(kind="facet.plc_channel", value="3" * 32),
        key=("f",),
        subject=template,
        signal=SignalType.AI_CURRENT,
        channel=1,
    )
    assert channel_signal(template, {template: facet}) is SignalType.AI_CURRENT
    assert channel_signal(_FUNCTION, {template: facet}) is None


def test_poles_of_one_function_of_a_bundle() -> None:
    """The invented relay: the coil pairs its pins, the changeover's two links are one pole."""
    bundle = relay_part_bundle()
    by_name = {f.name: f for f in bundle.function_templates}

    def poles(name: str) -> tuple[Pole, ...]:
        fn = by_name[name]
        ports = [t for t in bundle.port_templates if t.function == fn.id]
        return poles_of_template(fn.kind, ports, bundle.internal_links)

    assert _names(poles("coil")) == [("A1", "A2")]
    assert _names(poles("no_1")) == [("13", "14")]
    co_poles = poles("co_1")
    assert len(co_poles) == 2
    assert pole_count(co_poles) == 1


def test_conductor_of_stated_wins_then_the_marking_table_then_none() -> None:
    """A stated mark wins; else the marking (or name) is looked up in `CONDUCTOR_MARKS`."""
    assert conductor_of(_pin("U1")) is ConductorMark.L1
    assert conductor_of(_pin("+")) is ConductorMark.L_PLUS
    assert conductor_of(_pin("U1", mark=ConductorMark.L3)) is ConductorMark.L3
    assert conductor_of(_pin("13")) is None


def test_pole_pin_names_are_the_pins_on_a_pole_link() -> None:
    """A switched link's ends are pole pins; a plain conductive link of a contact is not."""
    links = [("13", "14", LinkKind.SWITCHED), ("x", "y", LinkKind.CONDUCTIVE)]
    assert pole_pin_names(FunctionKind.CONTACT_NO, links) == {"13", "14"}
    assert pole_pin_names(FunctionKind.PROTECTION, links) == {"13", "14", "x", "y"}


def test_contact_kinds_and_their_implied_rest() -> None:
    """A switch is a contact with no implied rest; a no or nc contact implies open or closed."""
    assert is_contact_kind(FunctionKind.SWITCH)
    assert not is_contact_kind(FunctionKind.COIL)
    assert implied_rest(FunctionKind.CONTACT_NO) == "open"
    assert implied_rest(FunctionKind.CONTACT_NC) == "closed"
    assert implied_rest(FunctionKind.CONTACT_CO) is None
    assert implied_rest(FunctionKind.SWITCH) is None
