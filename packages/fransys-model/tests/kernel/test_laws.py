"""REVIEW-M M2: the algebraic laws of the kernel as Hypothesis property tests.

Laws, each with a fixed `max_examples` (derandomized by the profile in `tests/conftest.py`):

1. Round trip: `from_data(to_data(m)) == m`, and the same through `dumps`/`loads`.
2. `merge` is commutative, associative and idempotent; a conflict raises `MergeConflict`.
3. `evolve(freeze(base), put, remove)` gives what `freeze` of the final records gives.
4. The digest does not depend on the order records were added in.

Each law is a checker in `laws_checks.py` that takes the implementation under test. The real laws
pass the real one; the `*_check_fails_*` tests pass a deliberately broken one and demand an
`AssertionError` (Hypothesis re-raises the failing example's own exception), so a check that could
never fail is caught. The strategies are in `laws_pool.py`, what the pools reach in
`test_laws_meta.py`.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st
from laws_checks import (
    check_associative,
    check_commutative,
    check_conflict,
    check_evolve,
    check_idempotent,
    check_insertion_order,
    check_round_trip,
    evolve_cases,
    freeze_records,
    merge_cases,
)
from laws_pool import Pool, pools

from fransys_model.kernel import Draft, Model, evolve, merge, to_data

if TYPE_CHECKING:
    from collections.abc import Callable

# Law 1: round trip.


@settings(max_examples=25)
@given(pool=pools())
def test_round_trip_gives_back_an_equal_model(pool: Pool) -> None:
    check_round_trip(pool)


# Law 2: merge.


@settings(max_examples=30)
@given(case=merge_cases())
def test_merge_is_commutative(case: Any) -> None:
    check_commutative(case)


@settings(max_examples=50)
@given(case=merge_cases())
def test_merge_is_associative(case: Any) -> None:
    check_associative(case)


@settings(max_examples=30)
@given(case=merge_cases())
def test_merge_is_idempotent(case: Any) -> None:
    check_idempotent(case)


@settings(max_examples=30)
@given(pool=pools(), data=st.data())
def test_a_conflict_raises_in_merge_and_in_evolve(pool: Pool, data: st.DataObject) -> None:
    check_conflict(pool, data.draw(st.sampled_from(pool.records)))


# Law 3: evolve gives what freeze gives.


@settings(max_examples=30)
@given(case=evolve_cases())
def test_evolve_gives_what_freeze_of_the_same_records_gives(case: Any) -> None:
    check_evolve(case)


# Law 4: insertion order.


@st.composite
def _insertion_cases(draw: st.DrawFn) -> tuple[Pool, list[Any], int]:
    pool = draw(pools())
    return pool, draw(st.permutations(pool.records)), draw(st.integers(0, len(pool.records) - 1))


@settings(max_examples=25)
@given(case=_insertion_cases())
def test_digest_does_not_depend_on_insertion_order(case: tuple[Pool, list[Any], int]) -> None:
    check_insertion_order(*case)


# Can-fail twins: the same checker with a broken implementation must raise `AssertionError`.


def _must_fail(check: Callable[..., None], cases: st.SearchStrategy[Any], broken: Any) -> None:
    """Run `check(*case, broken)` over 10 unshrunk examples; the check has to notice."""

    @settings(max_examples=10, phases=(Phase.generate,))
    @given(case=cases)
    def run(case: tuple[Any, ...]) -> None:
        check(*case, broken)

    with pytest.raises(AssertionError):
        run()


def _encoder_that_drops_aliases(model: Model) -> Any:
    return frozendict({**to_data(model), "aliases": ()})


def _merge_that_drops_the_middle_operand(*parts: Draft | Model) -> Draft:
    return merge(*parts[:1], *parts[2:]) if len(parts) > 2 else merge(*parts)


def _evolve_that_ignores_removals_of_unreplaced_records(
    model: Model, *, put: Any = (), remove: Any = (), origin: Any = None
) -> Model:
    replaced = {record.id for record in put}
    return evolve(model, put=put, remove=[i for i in remove if i in replaced], origin=origin)


def _freeze_that_digests_in_insertion_order(*args: Any, **kwargs: Any) -> Model:
    model = freeze_records(*args, **kwargs)
    ids = "".join(record.id.value for record in args[0])
    return dataclasses.replace(model, digest=ids)


def test_round_trip_check_fails_when_the_encoder_drops_aliases() -> None:
    _must_fail(check_round_trip, st.tuples(pools()), _encoder_that_drops_aliases)


def test_merge_check_fails_when_the_middle_operand_is_dropped() -> None:
    _must_fail(check_commutative, st.tuples(merge_cases()), _merge_that_drops_the_middle_operand)


def test_evolve_check_fails_when_removals_are_ignored() -> None:
    _must_fail(
        check_evolve,
        st.tuples(evolve_cases()),
        _evolve_that_ignores_removals_of_unreplaced_records,
    )


def test_insertion_order_check_fails_when_the_digest_follows_insertion_order() -> None:
    _must_fail(
        check_insertion_order,
        _insertion_cases(),
        _freeze_that_digests_in_insertion_order,
    )
