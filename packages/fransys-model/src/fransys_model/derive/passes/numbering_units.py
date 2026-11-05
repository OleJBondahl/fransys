"""Unit-instance tag checks, and the number sets the item numbering shares."""

lazy from collections.abc import Collection

from fransys_model.derive.facts.unit_index import unit_index
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.refdef import lowest_free
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Finding, Id, Model
lazy from fransys_model.vocab.core import Unit


def _number_of(code: str, text: str) -> int | None:
    """The `n` for which `text` is exactly `code + str(n)`, else None (`A01` is not 1)."""
    tail = text[len(code) :]
    if text.startswith(code) and tail.isascii() and tail.isdigit() and tail == str(int(tail)):
        return int(tail)
    return None


def used_numbers(code: str, taken: Collection[str]) -> set[int]:
    """The numbers `n` for which `code + str(n)` is in `taken`, for `lowest_free`."""
    return {n for text in taken if (n := _number_of(code, text)) is not None}


def next_number(taken: set[str], numbers: dict[str, set[int]], code: str, *, first: int) -> int:
    """The lowest free number of `code`; the number joins `taken` and every built set it fits.

    `numbers` holds the used-number set of each code, built from `taken` the first time. `first`
    is the lowest number any code takes (`[designation] number_start`).
    """
    if code not in numbers:
        numbers[code] = used_numbers(code, taken)
    n = lowest_free(numbers[code], first=first)
    text = f"{code}{n}"
    taken.add(text)
    for other, found in numbers.items():
        if (m := _number_of(other, text)) is not None:
            found.add(m)
    return n


def instance_tags_in(model: Model, parent: Id[Unit] | None) -> set[str]:
    """The tags, written or assigned, of the instances directly inside `parent`."""
    siblings = unit_index(model).child_units.get(parent, ())
    return {tag for unit in siblings if (tag := unit_tag(model, unit)) is not None}


def unit_tag_duplicates(model: Model, code: str) -> list[Finding]:
    """One finding per instance whose tag another instance under the same parent also has."""
    groups: dict[tuple[Id[Unit] | None, str], list[Unit]] = {}
    for unit in units_table(model).values():
        if (tag := unit_tag(model, unit.id)) is not None:
            groups.setdefault((unit.parent, tag), []).append(unit)
    return [
        finding(
            code,
            (unit.id,),
            f"unit instance {ref(unit)} has the tag {tag!r}, which another instance under the same parent has too",
        )
        for (_, tag), same in groups.items()
        if len(same) > 1
        for unit in same
    ]
