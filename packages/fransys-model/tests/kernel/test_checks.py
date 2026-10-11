"""Kernel checks: mutation-testing follow-up (decision 0022).

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

from fransys_model.kernel import Id, checks

# --- The alias-chain memo (checks.py:83) -------------------------------------------------


# --- `continue` -> `break` in record_problems (checks.py:112) ----------------------------


# --- The tie-break in Problem.sort_key (checks.py:35) ------------------------------------


# --- Every `Problem(...)` site pins stage/holder/path, checks.py side -------------------


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


# --- T-locator table: 7 refusal call sites, locators pinned, `why` text never asserted -------
