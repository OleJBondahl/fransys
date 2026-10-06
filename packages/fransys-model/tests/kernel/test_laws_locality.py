"""SC8: three locality laws, beside M2's kernel laws (`test_laws.py`).

Each law and its `*_check_fails_*` counterpart follow `test_laws.py`'s pattern: a real law must
pass, and a deliberately broken implementation of the same shape must be caught, so no law here
can pass vacuously (REVIEW-M M2).

1. Numbering: an item added to one numbering group -- `(unit, scope)`, `scope` the nearest
   board/harness the designation reads through (`derive.passes.numbering`, `number`'s
   docstring); here every item's scope is `None` (no boards), so the group is just the unit --
   changes no designation outside that group.
2. PLC allocation: a request added to one serving queue -- `(unit, signal)` -- changes no
   binding in another queue.
3. SC7: permuting the authored order of `InternalLink.a`/`b` (built via `laws_pool.pools()`,
   which already includes one `InternalLink` in every pool) leaves the whole model's digest
   unchanged.
"""

import dataclasses
import string
from collections import deque
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st
from laws_checks import freeze_records
from laws_pool import Pool, pools

from fransys_model.derive import item_designation
from fransys_model.derive.passes.numbering import number
from fransys_model.derive.passes.plc_allocation import allocate_plc
from fransys_model.kernel import Finding, Model, Origin, evolve, make_id
from fransys_model.vocab.core import Function, Item, Unit, UnitRelease
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of, functions, items, parts
from fransys_model.vocab.templates import FunctionTemplate, Part

if TYPE_CHECKING:
    from collections.abc import Callable

_ORIGIN = Origin(file="laws_locality.py", line=1, note="")

_RELAY = Part(
    id=make_id(Part, ("nl", "relay")),
    key=("nl", "relay"),
    mpn="NL-RELAY",
    manufacturer="Demo",
    description="",
    category=PartCategory.ELECTROMECHANICAL,
    class_code="K",
)


# Law 1: numbering.


@dataclasses.dataclass(frozen=True)
class _NumberingGroup:
    """One unit (its own release) and the items numbered within it."""

    release: UnitRelease
    unit: Unit
    items: tuple[Item, ...]


@st.composite
def _numbering_group(draw: st.DrawFn, prefix: str) -> _NumberingGroup:
    """A unit with 1-3 relay items; item 0 is always unnumbered, others maybe pre-tagged."""
    release = UnitRelease(
        id=make_id(UnitRelease, (prefix, "rel")),
        key=(prefix, "rel"),
        name=prefix,
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(
        id=make_id(Unit, (prefix, "unit")), key=(prefix, "unit"), release=release.id, parent=None
    )
    count = draw(st.integers(1, 3))
    built = []
    for i in range(count):
        tag = (
            None
            if i == 0
            else draw(st.none() | st.text(string.ascii_uppercase, min_size=1, max_size=2))
        )
        built.append(
            Item(
                id=make_id(Item, (prefix, "item", str(i))),
                key=(prefix, "item", str(i)),
                part=_RELAY.id,
                parent=None,
                position=None,
                tag=tag,
                description="",
                unit=unit.id,
            )
        )
    return _NumberingGroup(release, unit, tuple(built))


@st.composite
def numbering_locality_cases(draw: st.DrawFn) -> tuple[list[_NumberingGroup], Item]:
    """2-3 disjoint (unit, scope) groups; an extra unnumbered item is added to the FIRST.

    The extra item's key sorts before every other group's (a `g0` prefix precedes `g1`,
    `g2`, ...), so under the real pass it changes only group 0's own designations, and under
    a single-shared-counter pass it deterministically shifts every later group's numbers --
    the failing twin does not depend on which example Hypothesis happens to draw.
    """
    group_count = draw(st.integers(2, 3))
    groups = [draw(_numbering_group(f"g{g}")) for g in range(group_count)]
    extra = Item(
        id=make_id(Item, ("g0", "item", "extra")),
        key=("g0", "item", "extra"),
        part=_RELAY.id,
        parent=None,
        position=None,
        tag=None,
        description="",
        unit=groups[0].unit.id,
    )
    return groups, extra


def _numbering_records(groups: list[_NumberingGroup], extra: Item | None) -> list[Any]:
    records: list[Any] = [_RELAY]
    for group in groups:
        records.append(group.release)
        records.append(group.unit)
        records.extend(group.items)
    if extra is not None:
        records.append(extra)
    return records


def check_numbering_locality(
    case: tuple[list[_NumberingGroup], Item],
    number_impl: Callable[[Model], tuple[Model, tuple[Finding, ...]]] = number,
) -> None:
    """Adding `extra` to group 0 changes no designation of any item in another group."""
    groups, extra = case
    before, _ = number_impl(freeze_records(_numbering_records(groups, None), lambda _: _ORIGIN))
    after, _ = number_impl(freeze_records(_numbering_records(groups, extra), lambda _: _ORIGIN))
    for group in groups[1:]:
        for item in group.items:
            assert item_designation(before, item.id) == item_designation(after, item.id)


def _number_from_one_shared_counter(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Broken numbering: one global counter, no per-(unit, scope) grouping (law 1's probe)."""
    class_codes = {part.id: part.class_code for part in parts(model).values()}
    facets = []
    counter = 1
    for item in sorted(items(model).values(), key=lambda i: (i.key, i.id)):
        if item.tag is not None or item.part is None:
            continue
        code = class_codes[item.part]
        key = (*item.key, "assigned_designation")
        facets.append(
            AssignedDesignationFacet(
                id=make_id(AssignedDesignationFacet, key),
                key=key,
                subject=item.id,
                text=f"{code}{counter}",
            )
        )
        counter += 1
    if not facets:
        return model, ()
    return evolve(model, put=facets, origin=_ORIGIN), ()


@settings(max_examples=25)
@given(case=numbering_locality_cases())
def test_numbering_is_local_to_its_group(case: tuple[list[_NumberingGroup], Item]) -> None:
    check_numbering_locality(case)


# Law 2: PLC allocation.


@dataclasses.dataclass(frozen=True)
class _PlcGroup:
    """One unit with one DI channel module and one request bound to its one channel."""

    release: UnitRelease
    unit: Unit
    module_part: Part
    channel_template: FunctionTemplate
    channel_facet: PlcChannelFacet
    module_item: Item
    channel_function: Function
    request_item: Item
    request_function: Function
    request: PlcRequestFacet


def _plc_group(prefix: str) -> _PlcGroup:
    release = UnitRelease(
        id=make_id(UnitRelease, (prefix, "rel")),
        key=(prefix, "rel"),
        name=prefix,
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(
        id=make_id(Unit, (prefix, "unit")), key=(prefix, "unit"), release=release.id, parent=None
    )
    module_part = Part(
        id=make_id(Part, (prefix, "mod")),
        key=(prefix, "mod"),
        mpn="NL-DI",
        manufacturer="Demo",
        description="",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    channel_template = FunctionTemplate(
        id=make_id(FunctionTemplate, (prefix, "mod", "ch")),
        key=(prefix, "mod", "ch"),
        part=module_part.id,
        name="ch",
        kind=FunctionKind.PLC_CHANNEL,
    )
    channel_facet = PlcChannelFacet(
        id=make_id(PlcChannelFacet, (prefix, "mod", "ch", "facet")),
        key=(prefix, "mod", "ch", "facet"),
        subject=channel_template.id,
        signal=SignalType.DI,
        channel=1,
    )
    module_item = Item(
        id=make_id(Item, (prefix, "mod", "item")),
        key=(prefix, "mod", "item"),
        part=module_part.id,
        parent=None,
        position=1,
        tag="A1",
        description="",
        unit=unit.id,
    )
    channel_function = Function(
        id=make_id(Function, (prefix, "mod", "ch", "fn")),
        key=(prefix, "mod", "ch"),
        item=module_item.id,
        template=channel_template.id,
        name="ch",
        kind=FunctionKind.PLC_CHANNEL,
    )
    request_item = Item(
        id=make_id(Item, (prefix, "dev", "0")),
        key=(prefix, "dev", "0"),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="",
        unit=unit.id,
    )
    request_function = Function(
        id=make_id(Function, (prefix, "dev", "0", "fn")),
        key=(prefix, "dev", "0", "signal"),
        item=request_item.id,
        template=None,
        name="signal",
        kind=FunctionKind.SENSOR,
    )
    request = PlcRequestFacet(
        id=make_id(PlcRequestFacet, (prefix, "dev", "0", "signal", "request")),
        key=(prefix, "dev", "0", "signal", "request"),
        subject=request_function.id,
        signal=SignalType.DI,
        signal_name=f"tag_{prefix}",
        priority=1,
    )
    return _PlcGroup(
        release,
        unit,
        module_part,
        channel_template,
        channel_facet,
        module_item,
        channel_function,
        request_item,
        request_function,
        request,
    )


def _plc_extra_request(prefix: str, unit: Any) -> tuple[Item, Function, PlcRequestFacet]:
    """One more field device request for `prefix`'s unit -- its queue's channel is already taken."""
    item = Item(
        id=make_id(Item, (prefix, "dev", "1")),
        key=(prefix, "dev", "1"),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="",
        unit=unit,
    )
    function = Function(
        id=make_id(Function, (prefix, "dev", "1", "fn")),
        key=(prefix, "dev", "1", "signal"),
        item=item.id,
        template=None,
        name="signal",
        kind=FunctionKind.SENSOR,
    )
    request = PlcRequestFacet(
        id=make_id(PlcRequestFacet, (prefix, "dev", "1", "signal", "request")),
        key=(prefix, "dev", "1", "signal", "request"),
        subject=function.id,
        signal=SignalType.DI,
        signal_name=f"tag_{prefix}_extra",
        priority=1,
    )
    return item, function, request


@st.composite
def plc_locality_cases(
    draw: st.DrawFn,
) -> tuple[list[_PlcGroup], tuple[Item, Function, PlcRequestFacet]]:
    """2-3 groups, each one DI channel and one bound request; an extra request adds to group 0."""
    group_count = draw(st.integers(2, 3))
    groups = [_plc_group(f"g{g}") for g in range(group_count)]
    extra = _plc_extra_request("g0", groups[0].unit.id)
    return groups, extra


def _plc_records(
    groups: list[_PlcGroup], extra: tuple[Item, Function, PlcRequestFacet] | None
) -> list[Any]:
    records: list[Any] = []
    for group in groups:
        records += [
            group.release,
            group.unit,
            group.module_part,
            group.channel_template,
            group.channel_facet,
            group.module_item,
            group.channel_function,
            group.request_item,
            group.request_function,
            group.request,
        ]
    if extra is not None:
        records += list(extra)
    return records


def check_plc_locality(
    case: tuple[list[_PlcGroup], tuple[Item, Function, PlcRequestFacet]],
    allocate_impl: Callable[[Model], tuple[Model, tuple[Finding, ...]]] = allocate_plc,
) -> None:
    """Adding a request to group 0's queue changes no other group's binding."""
    groups, extra = case
    before, _ = allocate_impl(freeze_records(_plc_records(groups, None), lambda _: _ORIGIN))
    after, _ = allocate_impl(freeze_records(_plc_records(groups, extra), lambda _: _ORIGIN))
    before_by_subject = {b.subject: b for b in facets_of(before, PlcBindingFacet).values()}
    after_by_subject = {b.subject: b for b in facets_of(after, PlcBindingFacet).values()}
    for group in groups[1:]:
        subject = group.request.subject
        assert (subject in before_by_subject) == (subject in after_by_subject)
        if subject in before_by_subject:
            assert before_by_subject[subject].channel == after_by_subject[subject].channel


def _allocate_from_one_shared_queue(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Broken allocation: one global channel queue, ignoring which unit each belongs to."""
    all_functions = functions(model)
    modules = items(model)
    channel_templates = {f.subject for f in facets_of(model, PlcChannelFacet).values()}
    channel_functions = sorted(
        (fn for fn in all_functions.values() if fn.template in channel_templates),
        key=lambda fn: (modules[fn.item].key, fn.key, fn.id),
    )
    requests = sorted(
        facets_of(model, PlcRequestFacet).values(),
        key=lambda r: (r.priority, all_functions[r.subject].key, r.subject),
    )
    free = deque(channel_functions)
    bindings = []
    for request in requests:
        if not free:
            continue
        channel = free.popleft()
        key = (*all_functions[request.subject].key, "plc_binding")
        bindings.append(
            PlcBindingFacet(
                id=make_id(PlcBindingFacet, key),
                key=key,
                subject=request.subject,
                channel=channel.id,
            )
        )
    if not bindings:
        return model, ()
    return evolve(model, put=bindings, origin=_ORIGIN), ()


@settings(max_examples=25)
@given(case=plc_locality_cases())
def test_plc_allocation_is_local_to_its_queue(
    case: tuple[list[_PlcGroup], tuple[Item, Function, PlcRequestFacet]],
) -> None:
    check_plc_locality(case)


# Law 3: SC7 permutation invariance.


def check_link_permutation_invariant(
    pool: Pool, build: Callable[..., Model] = freeze_records, *, unsorted: bool = False
) -> None:
    """Permuting `InternalLink.a`/`b`'s authored order leaves the whole model's digest unchanged.

    `unsorted=True` simulates a `__post_init__` that never sorts (SC7's gap before this order):
    the swapped copy is forced back to its swapped fields instead of letting the real
    `__post_init__` re-normalise them, so this twin must fail.
    """
    link = next(record for record in pool.records if record.id.kind == "internal_link")
    swapped = dataclasses.replace(link, a=link.b, b=link.a)
    if unsorted:
        object.__setattr__(swapped, "a", link.b)
        object.__setattr__(swapped, "b", link.a)
    records = tuple(swapped if record is link else record for record in pool.records)
    original = build(pool.records, aliases=pool.aliases)
    permuted = build(records, aliases=pool.aliases)
    assert original.digest == permuted.digest


@settings(max_examples=25)
@given(pool=pools())
def test_permuting_an_internal_links_ends_leaves_the_digest_unchanged(pool: Pool) -> None:
    check_link_permutation_invariant(pool)


# Can-fail twins: the same checker with a broken implementation must raise `AssertionError`.


def _must_fail(check: Callable[..., None], cases: st.SearchStrategy[Any], **kwargs: Any) -> None:
    """Run `check(case, **kwargs)` over 10 unshrunk examples; the check has to notice."""

    @settings(max_examples=10, phases=(Phase.generate,))
    @given(case=cases)
    def run(case: Any) -> None:
        check(case, **kwargs)

    with pytest.raises(AssertionError):
        run()


def test_numbering_locality_check_fails_with_one_shared_counter() -> None:
    _must_fail(
        check_numbering_locality,
        numbering_locality_cases(),
        number_impl=_number_from_one_shared_counter,
    )


def test_plc_locality_check_fails_with_one_shared_queue() -> None:
    _must_fail(
        check_plc_locality, plc_locality_cases(), allocate_impl=_allocate_from_one_shared_queue
    )


def test_link_permutation_check_fails_when_stored_unsorted() -> None:
    _must_fail(check_link_permutation_invariant, pools(), unsorted=True)
