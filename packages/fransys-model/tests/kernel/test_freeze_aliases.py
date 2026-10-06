"""WP5 tests: aliases in `freeze()`, rewritten so a `Model` holds current ids (decision 0014)."""

from itertools import pairwise
from typing import Any, override

import pytest
from freeze_probes import (
    Derived,
    DerivedBefore,
    Facet,
    Holds,
    Pair,
    Refuser,
    draft_of,
    errors_of,
    holder_id,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_model.kernel import Id, Origin, RefError, SchemaError, ValueTypeError, freeze
from fransys_model.kernel.checks import ALIAS, ALIAS_FIELD, finals
from fransys_model.kernel.freeze import _rewrite_records


def test_a_reference_to_a_retired_id_is_rewritten_to_the_current_one(origin: Origin) -> None:
    """After freeze a record holds only current ids, wherever the reference sat."""
    old, new = owner_id("8"), owner_id("1")
    holder = make_holder(
        "2",
        owner=old,
        nested=Holds(owner=old, who=old),
        many=(old, new),
        anything=(old,),
        ext=frozendict({"x": (old,)}),
    )
    draft = draft_of(origin, holder, make_owner("1"))
    draft.alias(old, new)
    frozen: Any = freeze(draft).tables["freeze_holder_probe"][holder.id]
    assert frozen.owner == new
    assert frozen.nested.owner == new
    assert frozen.nested.who == new
    assert frozen.many == (new, new)
    assert frozen.anything == (new,)
    assert frozen.ext["x"] == (new,)


def test_a_record_that_mentions_no_retired_id_is_kept_as_the_same_object(origin: Origin) -> None:
    """Rewriting rebuilds only what changed."""
    untouched, touched = make_holder("2"), make_holder("3", owner=owner_id("8"))
    draft = draft_of(origin, untouched, touched, make_owner("1"))
    draft.alias(owner_id("8"), owner_id("1"))
    model = freeze(draft)
    assert model.tables["freeze_holder_probe"][untouched.id] is untouched
    assert model.tables["freeze_holder_probe"][touched.id] is not touched


def test_a_chain_of_aliases_leads_to_the_final_id_and_the_model_keeps_it_closed(
    origin: Origin,
) -> None:
    """Two renames of one key are normal: a to b to c, and `aliases` says a leads to c."""
    a, b, c = owner_id("7"), owner_id("8"), owner_id("1")
    draft = draft_of(origin, make_holder("2", owner=a), make_owner("1"))
    draft.alias(a, b)
    draft.alias(b, c)
    model = freeze(draft)
    rewritten: Any = model.tables["freeze_holder_probe"][holder_id("2")]
    assert rewritten.owner == c
    assert dict(model.aliases) == {a: c, b: c}


@pytest.mark.parametrize(
    ("aliases", "why"),
    [
        ([("8", "1"), ("1", "8")], "form a cycle"),
        ([("8", "9")], "names no record"),
        ([("2", "1")], "still have a record"),
    ],
    ids=["cycle", "missing-target", "old-still-exists"],
)
def test_an_alias_that_cannot_be_followed_is_a_ref_error_on_the_old_id(
    aliases: list[tuple[str, str]], why: str, origin: Origin
) -> None:
    """Every alias problem is a `RefError` whose holder is the retired id."""
    draft = draft_of(origin, make_owner("1"), make_owner("2"))
    for old, new in aliases:
        draft.alias(owner_id(old), owner_id(new))
    errors = errors_of(draft)
    assert all(isinstance(error, RefError) and error.field == "<alias>" for error in errors)
    assert any(why in str(error) for error in errors)
    assert {error.record_id for error in errors} <= {owner_id(old) for old, _ in aliases}


def test_two_facets_whose_subjects_alias_to_one_id_are_caught_by_unique(origin: Origin) -> None:
    """Aliases are resolved before the cardinality rules run, so a hidden duplicate shows."""
    old, new = owner_id("8"), owner_id("1")
    kind = "freeze_unique_probe"
    first = Facet(id=Id(kind=kind, value="1" * 32), key=("a",), subject=new)
    second = Facet(id=Id(kind=kind, value="2" * 32), key=("b",), subject=old)
    draft = draft_of(origin, first, second, make_owner("1"))
    draft.alias(old, new)
    (error,) = errors_of(draft)
    assert isinstance(error, SchemaError)
    assert error.record_id == second.id


def test_an_alias_that_makes_a_records_own_rule_refuse_is_a_problem_not_an_escape(
    origin: Origin,
) -> None:
    """Rebuilding a record re-runs `__post_init__`: `Pair` refuses two equal owners.

    What it raises joins the `FreezeError` instead of escaping `freeze()` on its own. The
    record is kept as authored, so its retired id also names no record: a second, true error.
    """
    old, new = owner_id("8"), owner_id("1")
    pair = Pair(id=Id(kind="freeze_pair_probe", value="3" * 32), key=("p",), first=old, second=new)
    draft = draft_of(origin, pair, make_owner("1"))
    draft.alias(old, new)
    refused, dangling = errors_of(draft)
    assert isinstance(refused, SchemaError)
    assert refused.record_id == pair.id
    assert refused.kind == "freeze_pair_probe"
    assert "two different owners" in str(refused)
    assert isinstance(dangling, RefError)
    assert dangling.target == old


def test_any_model_error_from_a_rewritten_records_own_rules_is_reported(origin: Origin) -> None:
    """Not only `SchemaError`: a `ValueTypeError` from `__post_init__` joins the `FreezeError`."""
    old, new = owner_id("8"), owner_id("1")
    kind = "freeze_refuser_probe"
    refuser = Refuser(id=Id(kind=kind, value="5" * 32), key=("r",), first=old, second=new)
    draft = draft_of(origin, refuser, make_owner("1"))
    draft.alias(old, new)
    refused, _ = errors_of(draft)
    assert isinstance(refused, ValueTypeError)
    assert "two different owners" in str(refused)


def test_a_long_chain_of_aliases_is_followed_to_its_end(origin: Origin) -> None:
    """Three thousand renames of one key: the reference reaches the final id, none is lost."""
    chain = [Id(kind="freeze_owner_probe", value=f"{n:032x}") for n in range(3000)]
    final = owner_id("1")
    draft = draft_of(origin, make_owner("1"), make_holder("2", owner=chain[0]))
    for retired, successor in zip(chain, [*chain[1:], final], strict=True):
        draft.alias(retired, successor)
    model = freeze(draft)
    holder: Any = model.tables["freeze_holder_probe"][holder_id("2")]
    assert holder.owner == final
    assert len(model.aliases) == 3000
    assert set(model.aliases.values()) == {final}


def test_following_a_chain_reads_each_link_a_bounded_number_of_times() -> None:
    """Counting reads, not seconds: a 2000-link chain is walked once, not once per link."""
    reads = []

    class Counting(frozendict):
        @override
        def __getitem__(self, key: Any) -> Any:
            reads.append(key)
            return super().__getitem__(key)

    chain = [Id(kind="freeze_owner_probe", value=f"{n:032x}") for n in range(2001)]
    ends = finals(Counting(pairwise(chain)))
    assert set(ends.values()) == {chain[-1]}
    assert len(reads) <= 2 * len(chain)


def test_an_id_in_a_field_that_init_does_not_take_follows_the_field_it_derives_from(
    origin: Origin,
) -> None:
    """`Derived.twin` is `init=False`: rewriting `owner` rebuilds it, and `replace` is not asked."""
    old, new = owner_id("8"), owner_id("1")
    derived = Derived(id=Id(kind="freeze_derived_probe", value="4" * 32), key=("d",), owner=old)
    draft = draft_of(origin, derived, make_owner("1"))
    draft.alias(old, new)
    frozen: Any = freeze(draft).tables["freeze_derived_probe"][derived.id]
    assert (frozen.owner, frozen.twin) == (new, new)


def test_a_field_after_a_derived_init_false_field_is_still_rewritten(origin: Origin) -> None:
    """`DerivedBefore.twin` sits BEFORE `owner`: the loop must not stop once it sees it.

    `Derived.twin` sits last, so it never exercises this: nothing follows it there.
    """
    old, new = owner_id("8"), owner_id("1")
    derived = DerivedBefore(
        id=Id(kind="freeze_derived_before_probe", value="6" * 32), key=("d",), owner=old
    )
    draft = draft_of(origin, derived, make_owner("1"))
    draft.alias(old, new)
    frozen: Any = freeze(draft).tables["freeze_derived_before_probe"][derived.id]
    assert frozen.owner == new


def test_a_retired_id_that_still_names_a_record_is_refused_before_rewrite_ever_sees_it(
    origin: Origin,
) -> None:
    """`close_aliases` never lets a record's own id become a key of the map `_rewrite` gets.

    So `_rewrite`'s per-field guard against rewriting a record's own `id` field has no case
    to protect: pinning this refusal's exact locators is what proves that.
    """
    old, new = owner_id("2"), owner_id("1")
    draft = draft_of(origin, make_owner("1"), make_owner("2"))
    draft.alias(old, new)
    (error,) = errors_of(draft)
    assert isinstance(error, RefError)
    assert str(error) == "a retired id must not still have a record of its own"
    assert (error.record_id, error.field, error.target) == (old, ALIAS_FIELD, new)


def test_rewrite_records_reports_a_refusal_problem_with_its_exact_locators() -> None:
    """A record whose rewrite raises is reported as an ALIAS-stage `Problem` on its own id."""
    old, new = owner_id("8"), owner_id("1")
    pair = Pair(id=Id(kind="freeze_pair_probe", value="3" * 32), key=("p",), first=old, second=new)
    _, problems = _rewrite_records((pair,), frozendict({old: new}))
    (problem,) = problems
    assert (problem.stage, problem.holder, problem.path) == (ALIAS, pair.id, ALIAS_FIELD)
