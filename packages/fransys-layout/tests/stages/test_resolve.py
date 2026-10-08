"""WP4: `stages.resolve` (ROADMAP WP4, docs/design/stages.md 6.1)."""

import dataclasses

import pytest
from samples import function_spec, hid

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES, kind_roles
from fransys_layout.geometry import (
    GENERIC_BOX_KEY,
    WIRING_GRID,
    Box,
    Facing,
    GeometryError,
    HintError,
    Orientation,
    Point,
    SymbolPortError,
    UnknownSymbolError,
)
from fransys_layout.stages import (
    PolePair,
    PortSpec,
    Role,
    SymbolChoice,
    SymbolRule,
    resolve,
)
from fransys_layout.stages.resolve import PIN_MAP_INCOMPLETE, SYMBOL_DEFAULTED, choice_index
from fransys_model.kernel import Severity

RULES = (SymbolRule(kind="contact_no", category=None, symbol="make-contact"),)
PORT_MAP = frozendict({"13": "in", "14": "out"})


def _choice(
    number: int,
    *,
    symbol: str,
    function: int | None = None,
    part: int | None = None,
    kind: str | None = None,
):
    return SymbolChoice(
        choice=hid("layout.symbol_choice", number),
        function=None if function is None else hid("function", function),
        part=None if part is None else hid("part", part),
        kind=kind,
        symbol=symbol,
        port_map=PORT_MAP,
    )


def _choice_map(number: int, symbol: str, port_map: dict[str, str]) -> SymbolChoice:
    """A function-level choice for function 1 with its own `port_map`."""
    return dataclasses.replace(
        _choice(number, symbol=symbol, function=1), port_map=frozendict(port_map)
    )


def test_kind_choice_binds_model_ports_through_the_port_map() -> None:
    """A kind choice draws the contact as `make-contact`, port `13` at `in`, `14` at `out`."""
    drawn, findings = resolve(
        (function_spec(1),),
        rules=RULES,
        choices=(_choice(1, symbol="make-contact", kind="contact_no"),),
    )
    (contact,) = drawn
    assert contact.geometry.key == "make-contact"
    assert {p.symbol_port for p in contact.ports} == {"in", "out"}
    assert (contact.primary_in, contact.primary_out) == ("in", "out")
    assert findings == ()


def test_function_choice_beats_kind_choice() -> None:
    """The most specific choice wins: function over kind."""
    choices = (
        _choice(1, symbol="make-contact", kind="contact_no"),
        _choice(2, symbol="break-contact", function=1),
    )
    drawn, _ = resolve((function_spec(1),), rules=RULES, choices=choices)
    assert drawn[0].geometry.key == "break-contact"


def test_two_equally_specific_choices_raise() -> None:
    """Two function-level choices for one function contradict each other."""
    choices = (
        _choice(1, symbol="make-contact", function=1),
        _choice(2, symbol="break-contact", function=1),
    )
    with pytest.raises(HintError):
        resolve((function_spec(1),), rules=RULES, choices=choices)


def test_model_port_missing_on_the_symbol_raises() -> None:
    """No port map, no equal name and no pole pair: port `13` has no symbol port."""
    unlinked = dataclasses.replace(function_spec(1), pole_pairs=())
    with pytest.raises(SymbolPortError) as excinfo:
        resolve((unlinked,), rules=RULES, choices=())
    assert excinfo.value.port_name == "13"


def test_unknown_symbol_key_raises() -> None:
    """A choice naming a symbol the library does not have raises; nothing is substituted."""
    with pytest.raises(UnknownSymbolError):
        resolve(
            (function_spec(1),), rules=RULES, choices=(_choice(1, symbol="no-such", function=1),)
        )


def test_function_with_no_symbol_is_a_generic_box_with_a_finding() -> None:
    """A `generic` function with no choice is drawn as a box and reported, not refused."""
    drawn, findings = resolve(
        (_with_part(function_spec(1, kind="generic")),), rules=RULES, choices=()
    )
    assert drawn[0].geometry.key == GENERIC_BOX_KEY
    assert len(drawn[0].geometry.ports) == 2
    assert [f.code for f in findings] == [SYMBOL_DEFAULTED]
    assert findings[0].subjects == (hid("function", 1),)


def _with_part(spec):
    """`spec` as a function of a part: `function_spec` has none, and that box is no finding."""
    return dataclasses.replace(spec, part=hid("part", 1))


def test_a_function_with_no_part_and_no_symbol_is_a_box_without_a_finding() -> None:
    """PATCH-0132 E4: a part-less box is its intended drawing, so `SYMBOL_DEFAULTED` skips it."""
    drawn, findings = resolve((function_spec(1, kind="generic"),), rules=RULES, choices=())
    assert drawn[0].geometry.key == GENERIC_BOX_KEY
    assert findings == ()


def test_the_default_terminal_rule_binds_a_lone_external_port_to_the_south_side() -> None:
    """PATCH-0132 E4: T2.21 carries `external` to `s`, for a terminal with no part."""
    spec = function_spec(1, kind="terminal")
    lone = dataclasses.replace(spec, ports=(dataclasses.replace(spec.ports[0], name="external"),))
    drawn, findings = resolve((lone,), rules=DEFAULT_RULES, choices=())
    assert [(p.symbol_port) for p in drawn[0].ports] == ["s"]
    assert findings == ()


def test_result_is_independent_of_input_order() -> None:
    """Shuffled inputs give the same output, sorted by function handle."""
    choices = (_choice(1, symbol="make-contact", kind="contact_no"),)
    specs = (function_spec(1), function_spec(2), function_spec(3))
    forward, _ = resolve(specs, rules=RULES, choices=choices)
    backward, _ = resolve(specs[::-1], rules=RULES, choices=choices)
    assert forward == backward


def test_a_rule_match_gives_no_finding_and_orientation_r0() -> None:
    """A kind with a table entry is drawn silently, always at `R0` in this engine."""
    drawn, findings = resolve((function_spec(1),), rules=RULES, choices=())
    assert drawn[0].geometry.key == "make-contact"
    assert drawn[0].geometry.orientation is Orientation.R0
    assert findings == ()


def test_a_pole_pair_maps_to_the_through_path_without_a_port_map() -> None:
    """No port map: the pole's ports, sorted by name, go to `in` and `out`."""
    drawn, _ = resolve((function_spec(1),), rules=RULES, choices=())
    assert {(p.port, p.symbol_port) for p in drawn[0].ports} == {
        (hid("port", 11), "in"),
        (hid("port", 12), "out"),
    }


def test_a_rule_port_map_beats_the_pole_pair_default() -> None:
    """A rule may carry a port map; here it draws the contact upside down."""
    rules = (
        SymbolRule(
            kind="contact_no",
            category=None,
            symbol="make-contact",
            port_map=frozendict({"13": "out", "14": "in"}),
        ),
    )
    drawn, _ = resolve((function_spec(1),), rules=rules, choices=())
    assert {(p.port, p.symbol_port) for p in drawn[0].ports} == {
        (hid("port", 11), "out"),
        (hid("port", 12), "in"),
    }


def test_a_rule_with_a_category_beats_one_without() -> None:
    """`contact_no` of a `protection` part takes the more specific row."""
    rules = (
        *RULES,
        SymbolRule(kind="contact_no", category="protection", symbol="break-contact"),
    )
    specific = dataclasses.replace(function_spec(1), category="protection")
    drawn, _ = resolve((specific, function_spec(2)), rules=rules, choices=())
    assert [d.geometry.key for d in drawn] == ["break-contact", "make-contact"]


def test_part_choice_sits_between_function_and_kind_choice() -> None:
    """Function beats part, part beats kind."""
    on_part = dataclasses.replace(function_spec(1), part=hid("part", 1))
    kind_choice = _choice(1, symbol="make-contact", kind="contact_no")
    part_choice = _choice(2, symbol="break-contact", part=1)
    function_choice = _choice(3, symbol="fuse", function=1)
    by_part, _ = resolve((on_part,), rules=RULES, choices=(kind_choice, part_choice))
    assert by_part[0].geometry.key == "break-contact"
    by_function, _ = resolve(
        (on_part,), rules=RULES, choices=(kind_choice, part_choice, function_choice)
    )
    assert by_function[0].geometry.key == "fuse"


def test_three_poles_bind_to_the_repeated_symbol() -> None:
    """Six model ports in three pole pairs are drawn at `1.in` .. `3.out`; pole 1 is primary."""
    names = ("1", "2", "3", "4", "5", "6")
    three = dataclasses.replace(
        function_spec(1),
        poles=3,
        pole_pairs=tuple(
            PolePair(index=i, first=names[2 * i], second=names[2 * i + 1]) for i in range(3)
        ),
        ports=tuple(
            PortSpec(
                port=hid("port", 10 + i), name=name, physical_net=hid("net", i), role=Role.POWER
            )
            for i, name in enumerate(names)
        ),
    )
    drawn, _ = resolve((three,), rules=RULES, choices=())
    assert drawn[0].geometry.poles == 3
    assert sorted(p.symbol_port for p in drawn[0].ports) == [
        "1.in", "1.out", "2.in", "2.out", "3.in", "3.out",
    ]  # fmt: skip
    assert (drawn[0].primary_in, drawn[0].primary_out) == ("1.in", "1.out")


def test_the_generic_box_names_its_ports_as_the_model_does() -> None:
    """Ports `13`, `14`: `13` on the N side, `14` on the S side, both on the wiring grid."""
    drawn, _ = resolve((function_spec(1, kind="generic"),), rules=RULES, choices=())
    geometry = drawn[0].geometry
    assert geometry.through is None
    assert [(p.name, p.facing) for p in geometry.ports] == [("13", Facing.N), ("14", Facing.S)]
    assert all(p.at.x % WIRING_GRID == 0 and p.at.y % WIRING_GRID == 0 for p in geometry.ports)
    assert (geometry.body.width, geometry.body.height) == (32, 32)
    # D5/D15: a box shows every port's marking, so each port has its own `marking.<port>` slot
    # beside the one `tag` slot (slots are sorted by name)
    assert [s.slot for s in geometry.slots] == ["marking.13", "marking.14", "tag"]
    assert (drawn[0].primary_in, drawn[0].primary_out) == ("13", "14")


def _spec(**changes):
    return dataclasses.replace(function_spec(1), **changes)


def _port(name: str, number: int) -> PortSpec:
    return PortSpec(
        port=hid("port", number), name=name, physical_net=hid("net", 0), role=Role.CONTROL
    )


def _generic(port_names: tuple[str, ...], **changes):
    ports = tuple(_port(name, 10 + i) for i, name in enumerate(port_names))
    return _spec(kind="generic", pole_pairs=(), ports=ports, **changes)


def test_two_model_ports_drawn_at_one_symbol_port_raise_and_name_both() -> None:
    """A `port_map` may not collapse two ports onto one; the other map is fine."""
    both_in = _choice_map(1, "make-contact", {"13": "in", "14": "in"})
    with pytest.raises(HintError) as excinfo:
        resolve((function_spec(1),), rules=RULES, choices=(both_in,))
    assert excinfo.value.subjects == (hid("function", 1), hid("port", 11), hid("port", 12))
    resolve(
        (function_spec(1),), rules=RULES, choices=(_choice(1, symbol="make-contact", function=1),)
    )


def test_a_port_map_target_that_is_not_a_symbol_port_raises() -> None:
    """The mapped name must exist on the chosen symbol; a valid target does not raise."""
    bent = _choice_map(1, "make-contact", {"13": "nope", "14": "out"})
    with pytest.raises(SymbolPortError) as excinfo:
        resolve((function_spec(1),), rules=RULES, choices=(bent,))
    assert excinfo.value.port_name == "13"
    valid = _choice_map(1, "make-contact", {"13": "in", "14": "out"})
    resolve((function_spec(1),), rules=RULES, choices=(valid,))


def test_a_function_without_a_part_matches_no_part_level_choice() -> None:
    """Kind choices for two kinds are not two part choices of a function that has no part."""
    choices = (
        _choice(1, symbol="make-contact", kind="contact_no"),
        _choice(2, symbol="break-contact", kind="contact_nc"),
    )
    drawn, _ = resolve((function_spec(1),), rules=(), choices=choices)
    assert drawn[0].geometry.key == "make-contact"


@pytest.mark.parametrize(("part", "kind"), [(1, None), (None, "contact_no")])
def test_two_equally_specific_part_or_kind_choices_raise(
    part: int | None, kind: str | None
) -> None:
    """The conflict rule holds at every level, and names the function and both choices."""
    spec = dataclasses.replace(function_spec(1), part=hid("part", 1))
    choices = (
        _choice(2, symbol="make-contact", part=part, kind=kind),
        _choice(1, symbol="break-contact", part=part, kind=kind),
    )
    with pytest.raises(HintError) as excinfo:
        resolve((spec,), rules=RULES, choices=choices)
    assert excinfo.value.subjects == (
        hid("function", 1),
        hid("layout.symbol_choice", 1),
        hid("layout.symbol_choice", 2),
    )


def test_a_rule_for_another_category_falls_back_to_the_plain_row() -> None:
    """A function of category `other` uses the row without a category."""
    rules = (*RULES, SymbolRule(kind="contact_no", category="protection", symbol="break-contact"))
    other = dataclasses.replace(function_spec(1), category="other")
    drawn, findings = resolve((other,), rules=rules, choices=())
    assert drawn[0].geometry.key == "make-contact"
    assert findings == ()


def test_a_category_only_row_does_not_match_a_function_without_a_category() -> None:
    """No plain row and no category on the function: the generic box, reported."""
    rules = (SymbolRule(kind="contact_no", category="protection", symbol="break-contact"),)
    drawn, findings = resolve((_with_part(function_spec(1)),), rules=rules, choices=())
    assert drawn[0].geometry.key == GENERIC_BOX_KEY
    assert [f.code for f in findings] == [SYMBOL_DEFAULTED]


def test_a_choice_port_map_beats_the_rule_port_map() -> None:
    """The choice's map wins over the rule's: here `13` stays at `in`."""
    rules = (
        SymbolRule(
            kind="contact_no",
            category=None,
            symbol="make-contact",
            port_map=frozendict({"13": "out", "14": "in"}),
        ),
    )
    drawn, _ = resolve(
        (function_spec(1),), rules=rules, choices=(_choice(1, symbol="make-contact", function=1),)
    )
    assert {(p.port, p.symbol_port) for p in drawn[0].ports} == {
        (hid("port", 11), "in"),
        (hid("port", 12), "out"),
    }


def test_an_unknown_symbol_in_a_rule_raises() -> None:
    """The rule path refuses an unknown key as the choice path does."""
    rules = (SymbolRule(kind="contact_no", category=None, symbol="no-such"),)
    with pytest.raises(UnknownSymbolError):
        resolve((function_spec(1),), rules=rules, choices=())


def test_repeating_a_symbol_without_a_through_path_raises() -> None:
    """`earth` at two poles is refused by the adapter and not caught here."""
    earth = _choice(1, symbol="earth", function=1)
    with pytest.raises(GeometryError):
        resolve((_spec(poles=2),), rules=RULES, choices=(earth,))


def test_the_through_path_names_decide_the_primary_ports() -> None:
    """A change-over contact runs `com` to `no`, so the pole pair binds and continues that way."""
    drawn, _ = resolve(
        (function_spec(1),), rules=(), choices=(_choice_map(1, "change-over-contact", {}),)
    )
    assert {(p.port, p.symbol_port) for p in drawn[0].ports} == {
        (hid("port", 11), "com"),
        (hid("port", 12), "no"),
    }
    assert (drawn[0].primary_in, drawn[0].primary_out) == ("com", "no")


def test_without_a_through_path_the_primaries_are_first_north_and_first_south() -> None:
    """`terminal` has ports n, e, s, w: primaries are `n` and `s`, whatever the port map says."""
    upright = _choice_map(1, "terminal", {"13": "n", "14": "s"})
    flipped = _choice_map(1, "terminal", {"13": "s", "14": "n"})
    for choice in (upright, flipped):
        drawn, _ = resolve((function_spec(1),), rules=(), choices=(choice,))
        assert (drawn[0].primary_in, drawn[0].primary_out) == ("n", "s")


def test_a_symbol_with_only_a_north_port_has_no_primary_out() -> None:
    """`earth` has one port, facing N: there is no southern port to continue to."""
    one_port = _spec(pole_pairs=(), ports=(_port("13", 11),))
    drawn, _ = resolve((one_port,), rules=(), choices=(_choice_map(1, "earth", {"13": "earth"}),))
    assert (drawn[0].primary_in, drawn[0].primary_out) == ("earth", None)


def test_the_generic_box_of_three_ports_has_two_pairs_and_a_wider_body() -> None:
    """Port i is at x = 2 M x (i // 2): ports 13, 14, 15 sit at (0, -2 M), (0, 2 M), (2 M, -2 M)."""
    drawn, _ = resolve((_generic(("13", "14", "15")),), rules=(), choices=())
    geometry = drawn[0].geometry
    assert [(p.name, p.at, p.facing) for p in geometry.ports] == [
        ("13", Point(x=0, y=-16), Facing.N),
        ("14", Point(x=0, y=16), Facing.S),
        ("15", Point(x=16, y=-16), Facing.N),
    ]
    assert geometry.body == Box(x=-16, y=-16, width=48, height=32)
    assert [(p.port, p.symbol_port) for p in drawn[0].ports] == [
        (hid("port", 10), "13"),
        (hid("port", 11), "14"),
        (hid("port", 12), "15"),
    ]


def test_the_generic_box_texts_start_at_fixed_anchors_and_grow_east() -> None:
    """D14: every text of a box has its near (west) edge at a fixed offset and grows east.

    The `tag` sits 0.5 M (4 G) right of the body's right edge (x = 16), level with its middle.
    A port's marking sits 0.25 M (2 G) east of its wire, 0.75 M (6 G) inside the body edge the
    port is on: port `13` at (0, -16) on the N edge, port `14` at (0, 16) on the S edge. D13 drops
    the fixed tag width (the measured text replaces it in `place`), so only the anchors and the
    facts a keep-out must keep are asserted, not the nominal box widths.
    """
    drawn, _ = resolve((function_spec(1, kind="generic"),), rules=(), choices=())
    geometry = drawn[0].geometry
    assert geometry.body == Box(x=-16, y=-16, width=32, height=32)
    anchors = {s.slot: (s.at, s.side, s.box.x) for s in geometry.slots}
    assert anchors == {
        "tag": (Point(x=20, y=0), Facing.E, 20),
        "marking.13": (Point(x=2, y=-10), Facing.E, 2),
        "marking.14": (Point(x=2, y=10), Facing.E, 2),
    }
    keepout = geometry.keepout
    for box in (geometry.body, *(s.box for s in geometry.slots)):
        assert keepout.x <= box.x
        assert keepout.y <= box.y
        assert box.x + box.width <= keepout.x + keepout.width
        assert box.y + box.height <= keepout.y + keepout.height
    assert (geometry.poles, geometry.orientation) == (1, Orientation.R0)


def test_a_generic_box_without_ports_is_the_minimum_body_and_has_no_primaries() -> None:
    """Zero ports: a 4 M x 4 M body, no ports, and nothing to continue a column through."""
    drawn, _ = resolve((_generic(()),), rules=(), choices=())
    assert drawn[0].geometry.body == Box(x=-16, y=-16, width=32, height=32)
    assert drawn[0].geometry.ports == ()
    assert (drawn[0].primary_in, drawn[0].primary_out) == (None, None)


def test_the_generic_box_is_never_repeated() -> None:
    """A three-pole function with no symbol is one box: `poles` is 1, and nothing is refused."""
    drawn, findings = resolve((_with_part(_generic(("13", "14"), poles=3)),), rules=(), choices=())
    assert drawn[0].geometry.poles == 1
    assert [f.code for f in findings] == [SYMBOL_DEFAULTED]


def test_the_defaulted_finding_is_info() -> None:
    """`SYMBOL_DEFAULTED` never blocks anything: severity `INFO`."""
    _, findings = resolve((_with_part(function_spec(1, kind="generic")),), rules=RULES, choices=())
    assert findings[0].severity is Severity.INFO


def test_a_terminal_with_two_of_four_ports_bound_has_no_finding() -> None:
    """`terminal`'s n/e/s/w are one node (`terminal.toml`): binding two of them is enough.

    A real terminal function normally binds only two of the four stub directions by
    design, and that is not an error, unlike the naive per-port form of this check.
    """
    choice = _choice_map(1, "terminal", {"13": "n", "14": "s"})
    drawn, findings = resolve((function_spec(1),), rules=(), choices=(choice,))
    assert len(drawn[0].geometry.ports) == 4
    assert [f for f in findings if f.code == PIN_MAP_INCOMPLETE] == []


def test_a_terminal_with_no_bound_port_is_one_finding_covering_all_four() -> None:
    """A `terminal` chosen for a function with no ports at all: one node, one finding."""
    empty = _generic(())
    drawn, findings = resolve((empty,), rules=(), choices=(_choice_map(1, "terminal", {}),))
    assert drawn[0].geometry.key == "terminal"
    assert len(drawn[0].geometry.ports) == 4
    incomplete = [f for f in findings if f.code == PIN_MAP_INCOMPLETE]
    assert len(incomplete) == 1
    assert incomplete[0].severity is Severity.ERROR
    assert incomplete[0].subjects == (hid("function", 1),)
    for name in ("n", "e", "s", "w"):
        assert name in incomplete[0].message


def test_a_change_over_contact_missing_nc_is_one_finding() -> None:
    """`nc` has no declared node of its own (`change-over-contact.toml`): its own singleton.

    The through path binds only `com` and `no` (as in
    `test_the_through_path_names_decide_the_primary_ports`), leaving `nc` unbound.
    """
    _, findings = resolve(
        (function_spec(1),), rules=(), choices=(_choice_map(1, "change-over-contact", {}),)
    )
    incomplete = [f for f in findings if f.code == PIN_MAP_INCOMPLETE]
    assert len(incomplete) == 1
    assert incomplete[0].severity is Severity.ERROR
    assert incomplete[0].subjects == (hid("function", 1),)
    assert "nc" in incomplete[0].message


def test_every_symbol_port_bound_is_no_finding() -> None:
    """`make-contact` binds both its ports through the kind choice: no incomplete finding."""
    drawn, findings = resolve(
        (function_spec(1),),
        rules=RULES,
        choices=(_choice(1, symbol="make-contact", kind="contact_no"),),
    )
    assert len(drawn[0].geometry.ports) == 2
    assert findings == ()


def test_result_and_findings_ignore_the_order_of_every_input() -> None:
    """Shuffling functions, rules and choices gives the same drawn functions and findings."""
    rules = (*RULES, SymbolRule(kind="contact_no", category="protection", symbol="break-contact"))
    choices = (
        _choice(1, symbol="make-contact", kind="contact_no"),
        _choice(2, symbol="break-contact", kind="contact_nc"),
    )
    specs = tuple(
        _with_part(function_spec(n, kind="generic" if n < 3 else "contact_no")) for n in (1, 2, 3)
    )
    forward = resolve(specs, rules=rules, choices=choices)
    backward = resolve(specs[::-1], rules=rules[::-1], choices=choices[::-1])
    assert forward == backward
    assert [f.subjects for f in forward[1]] == [(hid("function", 1),), (hid("function", 2),)]


def test_a_choice_map_and_a_rule_map_are_never_merged() -> None:
    """A choice with an empty map over a rule with a swapping map uses no rule entry."""
    rules = (
        SymbolRule(
            kind="contact_no",
            category=None,
            symbol="make-contact",
            port_map=frozendict({"13": "out", "14": "in"}),
        ),
    )
    plain = _choice_map(1, "make-contact", {})
    drawn, _ = resolve((function_spec(1),), rules=rules, choices=(plain,))
    assert {(p.port, p.symbol_port) for p in drawn[0].ports} == {
        (hid("port", 11), "in"),
        (hid("port", 12), "out"),
    }


def test_port_map_entries_no_port_uses_are_ignored_even_when_they_point_nowhere() -> None:
    """A kind-level map is shared by functions with different ports: unused entries are inert."""
    shared = _choice_map(1, "make-contact", {"13": "in", "14": "out", "99": "nope"})
    drawn, _ = resolve((function_spec(1),), rules=RULES, choices=(shared,))
    assert {p.symbol_port for p in drawn[0].ports} == {"in", "out"}


def test_choice_index_groups_by_function_part_and_kind_in_the_choices_order() -> None:
    """One pass groups the choices; each group keeps the order they came in (first wins)."""
    # UNDO: stages/resolve.py:choice_index, `by_key(choices, lambda choice: choice.function)`
    #     -> `by_key(reversed(choices), lambda choice: choice.function)` (the last choice leads)
    first = _choice(1, symbol="a", function=1)
    second = _choice(2, symbol="b", function=1)
    by_part = _choice(3, symbol="c", part=7)
    by_kind = _choice(4, symbol="d", kind="contact_no")
    index = choice_index((first, by_part, second, by_kind))
    assert index.by_function[hid("function", 1)] == (first, second)
    assert index.by_function[hid("function", 1)][0] is first
    assert index.by_part[hid("part", 7)] == (by_part,)
    assert index.by_kind["contact_no"] == (by_kind,)
    assert hid("function", 2) not in index.by_function


_CO_RULES = (SymbolRule(kind="contact_co", category=None, symbol="change-over-contact"),)
_THROWS = ("common", "break", "make")


def _changeover(names: tuple[str, str, str], throws: tuple[str | None, ...] = _THROWS):
    """Function 1 as a changeover: ports `names` (ids 10, 11, 12) with the throw `throws`."""
    ports = tuple(
        dataclasses.replace(_port(name, 10 + i), throw=throw)
        for i, (name, throw) in enumerate(zip(names, throws, strict=True))
    )
    return _spec(kind="contact_co", roles=kind_roles("contact_co"), pole_pairs=(), ports=ports)


@pytest.mark.parametrize(
    "names",
    [("11", "12", "14"), ("COM", "NC", "NO"), ("I", "II", "III"), ("NO", "COM", "NC")],
    ids=["digits", "com-nc-no", "roman", "names-that-lie"],
)
def test_a_changeover_binds_by_its_throw_roles_whatever_the_port_names(names) -> None:
    """Common -> `com`, break -> `nc`, make -> `no`; a common port named `NO` is still `com`."""
    # UNDO: stages/resolve.py:THROW_SYMBOL_PORTS, `"break": "nc"` -> `"break": "no"`
    drawn, findings = resolve((_changeover(names),), rules=_CO_RULES, choices=())
    assert {p.port: p.symbol_port for p in drawn[0].ports} == {
        hid("port", 10): "com",
        hid("port", 11): "nc",
        hid("port", 12): "no",
    }
    assert (drawn[0].primary_in, drawn[0].primary_out) == ("com", "no")
    assert findings == ()


def test_a_port_map_entry_for_a_throw_port_is_a_hint_error() -> None:
    """The roles are the one fact: a choice's or a rule's map may not rebind a throw port."""
    changeover = _changeover(("11", "12", "14"))
    rebinding = _choice_map(1, "change-over-contact", {"11": "no"})
    with pytest.raises(HintError) as excinfo:
        resolve((changeover,), rules=(), choices=(rebinding,))
    assert excinfo.value.subjects == (hid("function", 1), hid("port", 10))
    rule = dataclasses.replace(_CO_RULES[0], port_map=frozendict({"14": "com"}))
    with pytest.raises(HintError) as excinfo:
        resolve((changeover,), rules=(rule,), choices=())
    assert excinfo.value.subjects == (hid("function", 1), hid("port", 12))
    unused = _choice_map(1, "change-over-contact", {"99": "no"})  # names no port: inert
    resolve((changeover,), rules=(), choices=(unused,))


def test_a_changeover_without_throw_roles_keeps_its_old_binding() -> None:
    """A `GENERIC`-role changeover (Python-authored) binds by `port_map`, else by name."""
    generic = _changeover(("com", "nc", "no"), throws=(None, None, None))
    by_name, _ = resolve((generic,), rules=_CO_RULES, choices=())
    assert {p.port: p.symbol_port for p in by_name[0].ports} == {
        hid("port", 10): "com",
        hid("port", 11): "nc",
        hid("port", 12): "no",
    }
    swapped = _choice_map(1, "change-over-contact", {"com": "no", "no": "com"})
    by_map, _ = resolve((generic,), rules=(), choices=(swapped,))
    assert {p.port: p.symbol_port for p in by_map[0].ports} == {
        hid("port", 10): "no",
        hid("port", 11): "nc",
        hid("port", 12): "com",
    }
