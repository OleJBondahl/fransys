"""Kernel checks: mutation-testing follow-up (work order, decision 0022's trial, item B).

Targets `fransys_model.kernel.checks` directly -- never through `Draft`/`freeze()` --
so a walk order is exactly what the test built, not re-sorted underneath it. Kinds are
unique per test: the registries are global and never cleared, and these tests build raw
`Id`s and plain probe classes rather than `@record`-decorated ones wherever `checks.py`'s
functions only need `.id` (and, for cardinality, a `subject`-named attribute) -- they read
`vars(type(...))`, not the registry.

Locators (`Problem.stage`/`.holder`/`.path`, and an error's `.kind`/`.record_id`/`.field`/
`.target`) are pinned throughout; message wording (`why`) never is (CLAUDE.md: "one rule
computed in two places" is the model's problem, not a reason to pin prose here).
"""

from typing import Any

import pytest

from fransys_model.kernel import Id, RefError, SchemaError, checks
from fransys_model.kernel.conform import Reference

# --- B2: the alias-chain memo (checks.py:83) -------------------------------------------------


def test_finals_resolves_a_chain_whose_far_link_is_walked_first() -> None:
    """Iterating `{b: c, a: b}` visits `b` before `a`; both must still end at `c`.

    `b`'s own walk memoizes `finals[b] = c` first. `a`'s walk then hits `b`, which is
    already in the memo, and the code must read `c` back through it, not stop at `b`.
    """
    id_a = Id(kind="b2_probe", value="a" * 32)
    id_b = Id(kind="b2_probe", value="b" * 32)
    id_c = Id(kind="b2_probe", value="c" * 32)
    alias_map = frozendict({id_b: id_c, id_a: id_b})
    assert list(alias_map) == [id_b, id_a]  # the walk order the bug report assumes

    result = checks.finals(alias_map)

    assert result[id_a] == id_c
    assert result[id_b] == id_c


# --- B13: `continue` -> `break` in record_problems (checks.py:112) ----------------------------


def test_record_problems_walks_past_a_bad_kind_record_to_the_next(
    thing_cls: type, link_cls: type
) -> None:
    """A record of a bad kind is skipped, not a stop sign for the rest of the batch."""
    bad = thing_cls(id=Id(kind="thing", value="1" * 32), key=("bad",), name="x")
    owner_a = Id(kind="thing", value="2" * 32)
    owner_b = Id(kind="thing", value="3" * 32)
    good = link_cls(id=Id(kind="link", value="4" * 32), key=("good",), a=owner_a, b=owner_b)

    problems, references = checks.record_problems((bad, good), frozenset({"thing"}))

    assert problems == ()
    # Only reachable if the loop kept going past `bad` instead of breaking out of it.
    assert {holder for holder, _ in references} == {good.id}
    assert {reference.target for _, reference in references} == {owner_a, owner_b}


# --- B14: the tie-break in Problem.sort_key (checks.py:35) ------------------------------------


def test_problem_sort_key_ties_break_on_the_errors_own_text() -> None:
    """Same stage, holder and path: only `str(self.error)` can still tell the two apart."""
    holder = Id(kind="b14_probe", value="1" * 32)
    lower = checks.Problem(0, holder, "", SchemaError("aaa", kind="k"))
    higher = checks.Problem(0, holder, "", SchemaError("bbb", kind="k"))

    assert lower.sort_key() != higher.sort_key()
    assert sorted([higher, lower], key=checks.Problem.sort_key) == [lower, higher]


# --- B18: every `Problem(...)` site pins stage/holder/path, checks.py side -------------------


def test_close_aliases_problem_is_located_at_the_retired_id() -> None:
    """checks.py:62: `Problem(ALIAS, old, ALIAS_FIELD, error)`."""
    old = Id(kind="b18_ca", value="1" * 32)
    new = Id(kind="b18_ca", value="2" * 32)
    _closed, problems = checks.close_aliases(frozendict({old: new}), frozenset())

    (problem,) = problems
    assert problem.stage == checks.ALIAS
    assert problem.holder == old
    assert problem.path == checks.ALIAS_FIELD


def test_type_problems_problem_is_located_at_the_groups_first_id() -> None:
    """checks.py:100: `Problem(_SCHEMA, group[0].id, "", exc)`."""

    class NotARecord:
        key: Any = ("probe",)
        ext: Any = frozendict()

        def __init__(self, record_id: Id[Any]) -> None:
            self.id = record_id

    fake_id = Id(kind="b18_tp", value="3" * 32)
    bad, problems = checks.type_problems((("b18_tp", (NotARecord(record_id=fake_id),)),))

    assert bad == frozenset({"b18_tp"})
    (problem,) = problems
    assert problem.stage == checks._SCHEMA
    assert problem.holder == fake_id
    assert problem.path == ""


def test_record_problems_problem_is_located_at_the_records_id(thing_cls: type) -> None:
    """checks.py:117: `Problem(stage, record.id, path, error)`, the `SchemaError` branch."""
    bad = thing_cls(id=Id(kind="thing", value="5" * 32), key=("k",), name=123)

    problems, _references = checks.record_problems((bad,), frozenset())

    (problem,) = problems
    assert problem.stage == checks._SCHEMA
    assert problem.holder == bad.id
    assert problem.path == ""


def test_record_problems_pins_the_joined_path_for_a_value_type_error(thing_cls: type) -> None:
    """checks.py:116: `path = ".".join(error.path) if isinstance(error, ValueTypeError) else ""`.

    A `SchemaError` gives `path == ""` (above); a `ValueTypeError` (a bad leaf under `ext`,
    not a field-shape mismatch) must give the real dotted path, not an empty string or a
    differently-joined one (P13's mutmut rerun found this branch untested: B18 named
    checks.py:116-117 in scope, but every existing test only exercised the SchemaError half).
    """
    bad = thing_cls(
        id=Id(kind="thing", value="6" * 32),
        key=("k",),
        name="ok",
        ext=frozendict({"bad": frozenset()}),
    )

    problems, _references = checks.record_problems((bad,), frozenset())

    (problem,) = problems
    assert problem.stage == checks._VALUE
    assert problem.holder == bad.id
    assert problem.path == "ext.bad"


def test_reference_problems_problem_is_located_at_the_holder_and_field() -> None:
    """checks.py:135: `Problem(_REFERENCE, holder, reference.path, error)`."""
    holder = Id(kind="b18_rp", value="6" * 32)
    reference = Reference(path="owner", target=Id(kind="thing", value="7" * 32), kind=None)

    problems = checks.reference_problems(((holder, reference),), frozenset())

    (problem,) = problems
    assert problem.stage == checks._REFERENCE
    assert problem.holder == holder
    assert problem.path == "owner"


def test_cardinality_problems_problem_is_located_at_the_offending_record() -> None:
    """checks.py:158: `Problem(_CARDINALITY, record.id, "", SchemaError(...))`."""

    class SingletonProbe:
        __singleton__ = True
        key: Any = ("probe",)
        ext: Any = frozendict()

        def __init__(self, record_id: Id[Any]) -> None:
            self.id = record_id

    kind = "b18_cp"
    first = SingletonProbe(record_id=Id(kind=kind, value="8" * 32))
    second = SingletonProbe(record_id=Id(kind=kind, value="9" * 32))

    (problem,) = checks.cardinality_problems(((kind, (first, second)),))

    assert problem.stage == checks._CARDINALITY
    assert problem.holder == second.id
    assert problem.path == ""


# --- T-locator table: 7 refusal call sites, locators pinned, `why` text never asserted -------


@pytest.mark.parametrize("branch", ["own-record", "cycle", "missing-target"])
def test_close_aliases_refusal_locators_by_branch(branch: str) -> None:
    """T checks.py:53/55/57 (why text) and :61 (`target`): every branch's `RefError`.

    Each row mutates a `why` message or the `target` given to `RefError`. The message is
    not this test's business; `record_id`, `field` and `target` are.
    """
    old = Id(kind=f"t_ca_{branch}", value="1" * 32)
    new = Id(kind=f"t_ca_{branch}", value="2" * 32)
    if branch == "own-record":
        alias_map, ids = frozendict({old: new}), frozenset({old})
    elif branch == "cycle":
        alias_map, ids = frozendict({old: new, new: old}), frozenset()
    else:
        alias_map, ids = frozendict({old: new}), frozenset()

    _closed, problems = checks.close_aliases(alias_map, ids)
    problem = next(
        p for p in problems if isinstance(p.error, RefError) and p.error.record_id == old
    )

    error = problem.error
    assert isinstance(error, RefError)
    assert error.record_id == old
    assert error.field == checks.ALIAS_FIELD
    assert error.target == new
    assert problem.stage == checks.ALIAS
    assert problem.holder == old
    assert problem.path == checks.ALIAS_FIELD


def test_reference_problems_refusal_locators_for_a_dangling_target() -> None:
    """T checks.py:131: the "names no record" branch's `RefError`, locators only."""
    holder = Id(kind="t_rp", value="1" * 32)
    target = Id(kind="thing", value="2" * 32)
    reference = Reference(path="owner", target=target, kind=None)

    (problem,) = checks.reference_problems(((holder, reference),), frozenset())

    error = problem.error
    assert isinstance(error, RefError)
    assert error.record_id == holder
    assert error.field == "owner"
    assert error.target == target
    assert problem.stage == checks._REFERENCE
    assert problem.holder == holder
    assert problem.path == "owner"


@pytest.mark.parametrize("rule", ["singleton", "unique"])
def test_cardinality_problems_refusal_locators_by_rule(rule: str) -> None:
    """T checks.py:147/151: the `SchemaError`'s `.kind`/`.record_id`, not its `why` text."""
    kind = f"t_cp_{rule}"

    class Probe:
        __singleton__ = rule == "singleton"
        __unique__ = rule == "unique"
        __subject__ = "owner" if rule == "unique" else None
        key: Any = ("probe",)
        ext: Any = frozendict()

        def __init__(self, record_id: Id[Any], owner: Id[Any] | None = None) -> None:
            self.id = record_id
            self.owner = owner

    if rule == "singleton":
        first = Probe(record_id=Id(kind=kind, value="1" * 32))
        second = Probe(record_id=Id(kind=kind, value="2" * 32))
    else:
        subject = Id(kind="thing", value="9" * 32)
        first = Probe(record_id=Id(kind=kind, value="3" * 32), owner=subject)
        second = Probe(record_id=Id(kind=kind, value="4" * 32), owner=subject)

    (problem,) = checks.cardinality_problems(((kind, (first, second)),))

    error = problem.error
    assert isinstance(error, SchemaError)
    assert error.kind == kind
    assert error.record_id == second.id
    assert problem.stage == checks._CARDINALITY
    assert problem.holder == second.id
    assert problem.path == ""
