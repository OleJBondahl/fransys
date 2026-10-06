"""The evaluator of the conventions' tables: first match, rank key and keyed lookup.

Pure functions of a table, a subject and the facts the site passes in. What a decision does
with the result (an N/S cut, a chain's reverse) stays code at the site.
"""

from typing import TYPE_CHECKING

from .rows import Comb

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .facts import Fact
    from .rows import Cond, Order, Row, Table


def holds(cond: Cond, subject: object, facts: Mapping[str, Fact]) -> bool:
    """Whether `cond` holds for `subject`: a fact name is its truth, a pair its equality."""
    if isinstance(cond, str):
        return bool(facts[cond].func(subject))
    if not isinstance(cond, Comb):
        return facts[cond[0]].func(subject) == cond[1]
    results = [holds(arg, subject, facts) for arg in cond.args]
    return {"all": all(results), "any": any(results), "not": not results[0]}[cond.op]


def first_match(table: Table, subject: object, facts: Mapping[str, Fact]) -> Row | None:
    """The first row of `table` whose condition holds for `subject`, or None."""
    return next((r for r in table.rows if holds(r.when, subject, facts)), None)


def rank_key(order: Order, subject: object, facts: Mapping[str, Fact]) -> tuple[int, ...]:
    """One 0 or 1 per criterion, in order: 0 where the fact reads the preferred value."""
    return tuple(0 if facts[c.fact].func(subject) == c.prefer else 1 for c in order.criteria)


def keyed(table: Table, fact: str) -> dict[str, object]:
    """A keyed-lookup table as a dict: each row's `(fact, value)` atom gives value -> `then`."""
    pairs = [(r.when, r.then) for r in table.rows if isinstance(r.when, tuple)]
    return {when[1]: then for when, then in pairs if isinstance(when, tuple) and when[0] == fact}
