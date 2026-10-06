"""Cases and checkers for `test_laws.py`: each law is a plain function of an implementation.

`What == on a Model compares`: `schema_version`, `tables`, `aliases`, `hashes`, `digests` and
`digest`, but NOT `origins` (`compare=False`, design/kernel-records.md 5.4). So every check that
involves an origin (merge keeps the smaller one, evolve attributes its puts) also compares `origins`
by hand. `merge` returns a `Draft`, which has no `==`: drafts are compared as `state`, the triple
`(records(), origins(), alias_map())`.

A checker takes the drawn inputs and the implementation under test (default: the real one), so
the real law and its broken-implementation twin in `test_laws.py` share the same assertions.
"""

import dataclasses
from itertools import permutations
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import strategies as st
from laws_pool import Pool, pools

from fransys_model.kernel import (
    Draft,
    Id,
    MergeConflict,
    Model,
    Origin,
    dumps,
    evolve,
    freeze,
    from_data,
    loads,
    merge,
    to_data,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

BASE = Origin(file="base.py", line=1, note="")
PUT = Origin(file="pass.py", line=9, note="put")
OPERANDS = tuple(Origin(file=f"operand{j}.py", line=j, note="") for j in range(3))


def draft_of(
    records: Iterable[Any],
    origin_of: Callable[[Any], Origin] = lambda _: BASE,
    aliases: Iterable[tuple[Id[Any], Id[Any]]] = (),
) -> Draft:
    draft = Draft()
    for record in records:
        draft.add(record, origin=origin_of(record))
    for old, new in aliases:
        draft.alias(old, new)
    return draft


def freeze_records(
    records: Iterable[Any],
    origin_of: Callable[[Any], Origin] = lambda _: BASE,
    aliases: Iterable[tuple[Id[Any], Id[Any]]] = (),
) -> Model:
    return freeze(draft_of(records, origin_of, aliases))


def state(draft: Draft) -> tuple[Any, Any, Any]:
    return draft.records(), draft.origins(), draft.alias_map()


def touched(record: Any) -> Any:
    """`record` with different content and the same id."""
    return dataclasses.replace(record, ext=frozendict({"pass": "touched"}))


def closed(records: Iterable[Any]) -> tuple[Any, ...]:
    """The records that survive when every record with a reference to a missing id is dropped."""
    kept = {record.id: record for record in records}

    def refs(record: Any) -> set[Id[Any]]:
        found: set[Id[Any]] = set()
        stack = [getattr(record, f.name) for f in dataclasses.fields(record) if f.name != "id"]
        while stack:
            item = stack.pop()
            if type(item) is Id:
                found.add(item)
            elif type(item) is tuple:
                stack.extend(item)
            elif type(item) is frozendict:
                stack.extend(item.values())
        return found - {record.id}

    while missing := [i for i, record in kept.items() if not refs(record) <= kept.keys()]:
        for record_id in missing:
            del kept[record_id]
    return tuple(kept.values())


# Cases.


@dataclasses.dataclass(frozen=True)
class MergeCase:
    """A pool split into three overlapping operands whose union is the pool."""

    pool: Pool
    operands: tuple[tuple[Any, ...], ...]
    alias_sets: tuple[tuple[Any, ...], ...]

    def drafts(self) -> tuple[Draft, ...]:
        return tuple(
            draft_of(records, lambda _, j=j: OPERANDS[j], aliases)
            for j, (records, aliases) in enumerate(zip(self.operands, self.alias_sets, strict=True))
        )

    def expected(self) -> tuple[Any, Any, Any]:
        """What any merge of all three is: the pool, each record under its smallest origin."""
        ids = [{record.id for record in records} for records in self.operands]
        origins = {
            r.id: next(OPERANDS[j] for j in range(3) if r.id in ids[j]) for r in self.pool.records
        }
        ordered = tuple(sorted(self.pool.records, key=lambda record: record.id))
        return ordered, frozendict(origins), frozendict(self.pool.aliases)


@st.composite
def merge_cases(draw: st.DrawFn) -> MergeCase:
    pool = draw(pools())
    masks = draw(
        st.lists(st.integers(1, 7), min_size=len(pool.records), max_size=len(pool.records))
    )
    alias_masks = draw(
        st.lists(st.integers(1, 7), min_size=len(pool.aliases), max_size=len(pool.aliases))
    )
    operands = tuple(
        tuple(r for r, m in zip(pool.records, masks, strict=True) if m >> j & 1) for j in range(3)
    )
    alias_sets = tuple(
        tuple(a for a, m in zip(pool.aliases, alias_masks, strict=True) if m >> j & 1)
        for j in range(3)
    )
    return MergeCase(pool, operands, alias_sets)


@dataclasses.dataclass(frozen=True)
class EvolveCase:
    """A base and a final record set of one pool; `aliases` only when both hold its target."""

    base: tuple[Any, ...]
    final: tuple[Any, ...]
    aliases: tuple[tuple[Id[Any], Id[Any]], ...]


def evolve_plan(
    base: tuple[Any, ...], final: tuple[Any, ...]
) -> tuple[list[Any], list[Any], set[Any]]:
    """`put` and `remove` that turn `base` into `final`; a changed record is in both."""
    was = {record.id: record for record in base}
    now = {record.id: record for record in final}
    put = [record for record in final if was.get(record.id) != record]
    remove = [i for i, record in was.items() if now.get(i) != record]
    replaced = {i for i in remove if i in now}
    return put, remove, replaced


@st.composite
def evolve_cases(draw: st.DrawFn) -> EvolveCase:
    """Some records kept, some dropped, some changed; a valid alias when its target survives."""
    pool = draw(pools())
    records = pool.records
    in_base = draw(st.lists(st.integers(0, 9), min_size=len(records), max_size=len(records)))
    in_final = draw(st.lists(st.integers(0, 9), min_size=len(records), max_size=len(records)))
    base = closed(r for r, k in zip(records, in_base, strict=True) if k < 8)
    final = closed(
        touched(r) if k >= 8 else r for r, k in zip(records, in_final, strict=True) if k >= 2
    )
    kept = {r.id for r in base} & {r.id for r in final}
    aliases = tuple(pair for pair in pool.aliases if pair[1] in kept)
    return EvolveCase(base, final, aliases)


# Checkers.


def check_round_trip(pool: Pool, to_data_impl: Callable[[Model], Any] = to_data) -> None:
    """`from_data(to_data(m)) == m` and `loads(dumps(m)) == m`; aliases survive too."""
    model = freeze_records(pool.records, aliases=pool.aliases)
    data = to_data_impl(model)
    rebuilt = from_data(data)
    assert rebuilt == model
    assert loads(dumps(model)) == model
    assert to_data(rebuilt) == data
    assert dumps(rebuilt) == dumps(model)
    assert len(model.aliases) == len(pool.aliases)
    assert sum(len(table) for table in model.tables.values()) == len(pool.records)


def check_commutative(case: MergeCase, merge_impl: Callable[..., Draft] = merge) -> None:
    """Every order of the three operands gives one state; it is the pool, frozen or not."""
    a, b, c = case.drafts()
    for order in permutations((a, b, c)):
        assert state(merge_impl(*order)) == case.expected()
    assert state(merge_impl(a, b)) == state(merge_impl(b, a))
    whole = freeze_records(case.pool.records, aliases=case.pool.aliases)
    assert freeze(merge_impl(c, b, a)) == whole


def check_associative(case: MergeCase, merge_impl: Callable[..., Draft] = merge) -> None:
    """`merge(merge(a, b), c)` and `merge(a, merge(b, c))` have one state, the flat merge's."""
    a, b, c = case.drafts()
    left = merge_impl(merge_impl(a, b), c)
    right = merge_impl(a, merge_impl(b, c))
    assert state(left) == state(right) == case.expected()


def check_idempotent(case: MergeCase, merge_impl: Callable[..., Draft] = merge) -> None:
    """Merging a part with itself adds nothing, for drafts and for a frozen `Model`."""
    a, b, c = case.drafts()
    assert state(merge_impl(a, a)) == state(a)
    assert state(merge_impl(a, b, a, b)) == state(merge_impl(a, b))
    model = freeze(merge_impl(a, b, c))
    twice = merge_impl(model, model)
    assert state(twice) == state(merge_impl(model))
    assert freeze(twice) == model


def check_conflict(
    pool: Pool,
    record: Any,
    merge_impl: Callable[..., Draft] = merge,
    evolve_impl: Callable[..., Model] = evolve,
) -> None:
    """The same id with other content is a `MergeConflict` naming the id and both origins."""
    other = touched(record)
    whole = draft_of(pool.records, lambda _: OPERANDS[0])
    single = draft_of((other,), lambda _: OPERANDS[1])
    for order in ((whole, single), (single, whole)):
        with pytest.raises(MergeConflict) as caught:
            merge_impl(*order)
        assert caught.value.record_id == record.id
        assert {caught.value.origin_a, caught.value.origin_b} == set(OPERANDS[:2])
    model = freeze_records(pool.records, aliases=pool.aliases)
    with pytest.raises(MergeConflict) as caught:
        evolve_impl(model, put=(other,), origin=PUT)
    assert caught.value.record_id == record.id
    assert {caught.value.origin_a, caught.value.origin_b} == {BASE, PUT}


def check_evolve(case: EvolveCase, evolve_impl: Callable[..., Model] = evolve) -> None:
    """`evolve(freeze(base), put, remove)` equals `freeze(final)`, origins and aliases included."""
    put, remove, _ = evolve_plan(case.base, case.final)
    model = freeze_records(case.base, aliases=case.aliases)
    evolved = evolve_impl(model, put=tuple(reversed(put)), remove=remove, origin=PUT)
    put_ids = {record.id for record in put}
    expected = freeze_records(case.final, lambda r: PUT if r.id in put_ids else BASE, case.aliases)
    assert len(model.aliases) == len(case.aliases)
    assert evolved.aliases == model.aliases
    assert evolved == expected
    assert evolved.origins == expected.origins
    assert dumps(evolved) == dumps(expected)


def check_insertion_order(
    pool: Pool,
    shuffled: list[Any],
    changed: int,
    build: Callable[..., Model] = freeze_records,
) -> None:
    """Records added in any order, with any origins, freeze to one model; a change moves it."""
    lines = {record.id: line for line, record in enumerate(shuffled)}
    first = build(pool.records, aliases=pool.aliases)
    second = build(
        shuffled, lambda r: Origin(file="z.py", line=lines[r.id], note=""), reversed(pool.aliases)
    )
    assert first == second
    assert (first.digest, first.digests, first.hashes) == (
        second.digest,
        second.digests,
        second.hashes,
    )
    edited = [touched(r) if i == changed else r for i, r in enumerate(pool.records)]
    assert build(edited, aliases=pool.aliases).digest != first.digest
