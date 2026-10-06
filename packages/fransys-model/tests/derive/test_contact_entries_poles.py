"""A contact's image pairs come from its declared pole links, not from consecutive numbers (F4).

`contact_entries` reads `vocab.markings.function_poles`, so a part whose poles join 1-3 and 2-4
lists `1-3` and `2-4`; pairing the sorted numbers odd-even would give `1-2` and `3-4`.
"""

import pytest
from contact_builders import _ITEM_KEY, _PART_KEY, _model

from fransys_model.derive.contact_entries import _is_main, contact_entries
from fransys_model.kernel import Origin, make_id
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind, LinkKind, LinkRest, PartCategory, PortRole
from fransys_model.vocab.instantiate import PartBundle
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate


def _two_pole_bundle(
    joins: tuple[tuple[str, str], ...], markings: dict[str, str] | None = None
) -> PartBundle:
    """One NO contact with ports 1 to 4 and a switched, rest-open link per pair in `joins`."""
    part = Part(
        id=make_id(Part, _PART_KEY),
        key=_PART_KEY,
        mpn="EF-POLES-1",
        manufacturer="Example Co",
        description="Invented two-pole contact for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    fkey = (*_PART_KEY, "fn", "no")
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, fkey),
        key=fkey,
        part=part.id,
        name="no",
        kind=FunctionKind.CONTACT_NO,
    )
    ports = {
        name: PortTemplate(
            id=make_id(PortTemplate, (*fkey, "port", name)),
            key=(*fkey, "port", name),
            function=function.id,
            name=name,
            role=PortRole.GENERIC,
            marking=(markings or {}).get(name),
        )
        for name in "1234"
    }
    links = tuple(
        InternalLink(
            id=make_id(InternalLink, (*fkey, "link", a, b)),
            key=(*fkey, "link", a, b),
            a=ports[a].id,
            b=ports[b].id,
            kind=LinkKind.SWITCHED,
            rest=LinkRest.OPEN,
        )
        for a, b in joins
    )
    return PartBundle(
        part=part,
        function_templates=(function,),
        port_templates=tuple(ports.values()),
        internal_links=links,
    )


def test_the_pairs_follow_the_declared_links_not_odd_even_numbers(origin: Origin) -> None:
    """Poles joining 1-3 and 2-4 list `1-3` and `2-4`, in marking order."""
    # UNDO: derive/contact_entries.py:_poles, `if found:` -> `if False:` (odd-even zip)
    model = _model(_two_pole_bundle((("2", "4"), ("1", "3"))), origin)
    function = make_id(Function, (*_ITEM_KEY, "fn", "no"))

    no, nc = contact_entries(model, functions(model)[function])
    assert [(key, mark) for _, key, mark in no] == [(1, "1-3"), (2, "2-4")]
    assert nc == []


def test_with_no_pole_link_the_pins_pair_in_marking_order(origin: Origin) -> None:
    """No link: pins marked 1, 3, 2, 4 (names 1, 2, 3, 4) pair by marking, not by name."""
    # UNDO: derive/contact_entries.py:_poles, the fallback back to a local sort of the names
    marks = {"1": "1", "2": "3", "3": "2", "4": "4"}
    model = _model(_two_pole_bundle((), marks), origin)
    function = make_id(Function, (*_ITEM_KEY, "fn", "no"))

    no, _ = contact_entries(model, functions(model)[function])
    assert [(key, mark) for _, key, mark in no] == [(1, "1-3"), (2, "2-4")]


def test_a_pole_with_single_digit_pins_is_main_whatever_the_pole_count(origin: Origin) -> None:
    """One pole 1-2 and two poles 1-3, 2-4 are all main: the pole count never decides (D7)."""
    # UNDO: derive/contact_entries.py:_is_main, back to `len(pairs) == 1`
    one = _model(_two_pole_bundle((("1", "2"),)), origin)
    two = _model(_two_pole_bundle((("1", "3"), ("2", "4"))), origin)
    function = make_id(Function, (*_ITEM_KEY, "fn", "no"))
    for model in (one, two):
        no, _ = contact_entries(model, functions(model)[function])
        assert no
        assert all(main for main, _, _ in no)


@pytest.mark.parametrize(
    ("line", "load", "main"),
    [
        ("1", "2", True),
        ("5", "6", True),
        ("13", "14", False),
        ("95", "96", False),
        ("A", "B", False),
        ("1", "14", False),
    ],
)
def test_main_against_auxiliary_by_the_printed_pin_names(
    line: str, load: str, *, main: bool
) -> None:
    """Single-digit numbers on both pins are main (1, 1/L1 print as 1); else auxiliary."""
    assert _is_main(line, load) is main
