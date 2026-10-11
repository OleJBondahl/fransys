"""Tests of `stages.resolve`."""

import dataclasses

import pytest
from samples import function_spec, hid

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES, kind_roles
from fransys_layout.geometry import (
    GENERIC_BOX_KEY,
    Box,
    HintError,
    SymbolPortError,
)
from fransys_layout.stages import (
    PortSpec,
    Role,
    SymbolChoice,
    SymbolRule,
    resolve,
)
from fransys_layout.stages.resolve import PIN_MAP_INCOMPLETE, choice_index
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


def test_function_choice_beats_kind_choice() -> None:
    """The most specific choice wins: function over kind."""
    choices = (
        _choice(1, symbol="make-contact", kind="contact_no"),
        _choice(2, symbol="break-contact", function=1),
    )
    drawn, _ = resolve((function_spec(1),), rules=RULES, choices=choices)
    assert drawn[0].geometry.key == "break-contact"


def _with_part(spec):
    """`spec` as a function of a part: `function_spec` has none, and that box is no finding."""
    return dataclasses.replace(spec, part=hid("part", 1))


def test_a_function_with_no_part_and_no_symbol_is_a_box_without_a_finding() -> None:
    """A part-less box is its intended drawing, so `SYMBOL_DEFAULTED` skips it."""
    drawn, findings = resolve((function_spec(1, kind="generic"),), rules=RULES, choices=())
    assert drawn[0].geometry.key == GENERIC_BOX_KEY
    assert findings == ()


def test_the_default_terminal_rule_binds_a_lone_external_port_to_the_south_side() -> None:
    """The default terminal rule carries `external` to `s`, for a terminal with no part."""
    spec = function_spec(1, kind="terminal")
    lone = dataclasses.replace(spec, ports=(dataclasses.replace(spec.ports[0], name="external"),))
    drawn, findings = resolve((lone,), rules=DEFAULT_RULES, choices=())
    assert [(p.symbol_port) for p in drawn[0].ports] == ["s"]
    assert findings == ()


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


def test_a_generic_box_without_ports_is_the_minimum_body_and_has_no_primaries() -> None:
    """Zero ports: a 4 M x 4 M body, no ports, and nothing to continue a column through."""
    drawn, _ = resolve((_generic(()),), rules=(), choices=())
    assert drawn[0].geometry.body == Box(x=-16, y=-16, width=32, height=32)
    assert drawn[0].geometry.ports == ()
    assert (drawn[0].primary_in, drawn[0].primary_out) == (None, None)


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
