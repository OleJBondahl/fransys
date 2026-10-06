"""Rows, criteria and tables: the conventions as data (spec C5, decision layout-0111).

A condition is an atom or a combination. An atom is a boolean fact name, or a pair
`(fact, value)` tested by equality; a combination is built by `all_`, `any_` and `not_`
only. There are no loops and no user functions. A `Table` is a first-match or keyed-lookup
list of rows; an `Order` is a list of criteria. `problems` finds an unknown fact name or a
value outside the fact's set, and `validate` raises on one.
"""

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .facts import Fact

POLICIES = ("first match", "rank key", "keyed lookup")


class Comb(NamedTuple):
    """A combination of conditions: `op` is all, any or not."""

    op: str
    args: tuple[Cond, ...]


Atom = str | tuple[str, str]
Cond = Atom | Comb


def all_(*conds: Cond) -> Comb:
    """True when every condition holds."""
    return Comb("all", conds)


def any_(*conds: Cond) -> Comb:
    """True when one condition holds."""
    return Comb("any", conds)


def not_(cond: Cond) -> Comb:
    """True when the condition does not hold."""
    return Comb("not", (cond,))


class Row(NamedTuple):
    """One row of a table: when `when` holds, the decision is `then`."""

    id: str
    when: Cond
    then: object


class Criterion(NamedTuple):
    """One criterion of an order: the subject whose `fact` reads `prefer` ranks first."""

    id: str
    fact: str
    prefer: bool | str


class Table(NamedTuple):
    """A table of rows; `policy` is "first match" or "keyed lookup"."""

    name: str
    policy: str
    rows: tuple[Row, ...]


class Order(NamedTuple):
    """A table of criteria; the first criterion that separates two subjects decides."""

    name: str
    criteria: tuple[Criterion, ...]
    policy: str = "rank key"


def _atoms(cond: Cond) -> list[Atom]:
    if isinstance(cond, Comb):
        return [atom for arg in cond.args for atom in _atoms(arg)]
    return [cond]


def _atom_problem(atom: Atom, facts: Mapping[str, Fact]) -> str | None:
    name, value = (atom, None) if isinstance(atom, str) else atom
    found = facts.get(name)
    if found is None:
        return f"unknown fact {name!r}"
    if value is not None and (found.values is None or value not in found.values):
        return f"value {value!r} is outside the set of fact {name!r}"
    return None


def _criterion_atom(row: Criterion) -> Atom:
    return row.fact if isinstance(row.prefer, bool) else (row.fact, row.prefer)


def problems(table: Table | Order, facts: Mapping[str, Fact]) -> list[str]:
    """Every unknown fact name, out-of-set value and bad policy in `table`, with its row id."""
    found = [] if table.policy in POLICIES else [f"{table.name}: policy {table.policy!r}"]
    pairs = (
        [(c.id, _criterion_atom(c)) for c in table.criteria]
        if isinstance(table, Order)
        else [(r.id, a) for r in table.rows for a in _atoms(r.when)]
    )
    found += [f"{table.name} {i}: {p}" for i, a in pairs if (p := _atom_problem(a, facts))]
    return found


def validate(table: Table | Order, facts: Mapping[str, Fact]) -> None:
    """Raise `ValueError` when `table` names an unknown fact or a value outside a fact's set."""
    if found := problems(table, facts):
        raise ValueError("; ".join(found))
