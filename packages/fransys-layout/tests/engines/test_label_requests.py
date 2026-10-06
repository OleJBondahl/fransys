"""`label_requests`: every first-pass request with its final slot, after `resolve` (layout-0027)."""

import dataclasses
from typing import TYPE_CHECKING

from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.labels import label_requests
from fransys_layout.stages import LabelKind, resolve
from fransys_model.derive import wire_rows
from fransys_model.kernel import freeze

if TYPE_CHECKING:
    from fransys_layout.stages import DrawnFunction, LabelRequest


def _requests() -> tuple[tuple[DrawnFunction, ...], tuple[LabelRequest, ...]]:
    inputs = read_inputs(freeze(build_cabinet()))
    drawn, _ = resolve(inputs.functions, rules=DEFAULT_RULES, choices=inputs.choices)
    return drawn, label_requests(inputs.label_texts, drawn)


def _function_key(drawn: tuple[DrawnFunction, ...], *key: str) -> DrawnFunction:
    (found,) = (fn for fn in drawn if fn.key == key)
    return found


def test_a_marking_slot_names_the_symbol_port_after_the_port_map() -> None:
    """A pole-through-path port is `1.in`, so its slot is `marking.1.in`, not `marking.1`."""
    drawn, requests = _requests()
    port_of = {p.port: p.symbol_port for fn in drawn for p in fn.ports}
    markings = [r for r in requests if r.kind is LabelKind.MARKING]
    assert markings
    for request in markings:
        assert request.slot == f"marking.{port_of[request.subject]}"
    main = _function_key(drawn, "cabinet", "k1", "fn", "main")
    assert {p.symbol_port for p in main.ports} == {
        "1.in",
        "2.in",
        "3.in",
        "1.out",
        "2.out",
        "3.out",
    }
    slots = {r.slot for r in markings if r.subject in {p.port for p in main.ports}}
    assert slots == {
        f"marking.{name}" for name in ("1.in", "2.in", "3.in", "1.out", "2.out", "3.out")
    }


def test_every_symbol_slot_request_names_a_slot_its_symbol_defines() -> None:
    """`place_slot_labels` raises on any other; nothing rewrites a slot after this call."""
    drawn, requests = _requests()
    function_of = {p.port: fn for fn in drawn for p in fn.ports} | {fn.function: fn for fn in drawn}
    for request in requests:
        if request.kind is LabelKind.WIRE:
            continue
        slots = {slot.slot for slot in function_of[request.subject].geometry.slots}
        assert request.slot in slots


def test_a_symbol_without_marking_slots_gets_no_marking_request() -> None:
    """A terminal symbol has a `tag` slot only: it gets its TAG and no MARKING."""
    drawn, requests = _requests()
    terminal = _function_key(drawn, "cabinet", "x1", "1", "fn", "terminal")
    assert {slot.slot for slot in terminal.geometry.slots} == {"tag"}
    mine = [
        r for r in requests if r.subject in {terminal.function, *(p.port for p in terminal.ports)}
    ]
    assert [(r.kind, r.slot) for r in mine] == [(LabelKind.TAG, "tag")]


def test_a_symbol_without_a_tag_slot_gets_no_tag_request() -> None:
    """The condition is the chosen symbol's own slots: strip them and every request goes."""
    inputs = read_inputs(freeze(build_cabinet()))
    drawn, _ = resolve(inputs.functions, rules=DEFAULT_RULES, choices=inputs.choices)
    bare = dataclasses.replace(drawn[0], geometry=dataclasses.replace(drawn[0].geometry, slots=()))
    requests = label_requests(inputs.label_texts, (bare,))
    assert [r for r in requests if r.kind is not LabelKind.WIRE] == []


def test_a_labelled_conductor_gives_no_wire_request() -> None:
    """V8 (owner 2026-10-02): a schematic page prints no wire label; the wire list holds it."""
    inputs = read_inputs(freeze(build_cabinet()))
    _, requests = _requests()
    assert {r.kind for r in requests} >= {LabelKind.TAG, LabelKind.MARKING}
    assert LabelKind.WIRE not in {r.kind for r in requests}
    assert LabelKind.WIRE not in {t.kind for t in inputs.label_texts}
    assert wire_rows(freeze(build_cabinet()))


def test_requests_are_sorted_by_kind_subject_and_slot() -> None:
    """One explicit order, whatever the order of the drawn functions."""
    inputs = read_inputs(freeze(build_cabinet()))
    drawn, _ = resolve(inputs.functions, rules=DEFAULT_RULES, choices=inputs.choices)
    forward = label_requests(inputs.label_texts, drawn)
    backward = label_requests(tuple(reversed(inputs.label_texts)), tuple(reversed(drawn)))
    assert forward == backward
    assert list(forward) == sorted(forward, key=lambda r: (r.kind.value, r.subject, r.slot))
