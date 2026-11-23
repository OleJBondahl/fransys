"""Diff of the unit, item, nested-unit and boundary sections."""

from typing import TYPE_CHECKING, cast

from fransys_model.kernel import JsonValue, value_data, write_json

from .baseline_diff_rows import presence_changes, sort_changes
from .order import natural_key
from .revision_text import revision_text
from .rows_baseline import BaselineBoundary, BaselineItem, BaselineNestedUnit, BaselineUnit, Change

if TYPE_CHECKING:
    from fransys_model.elecdef import Rating
    from fransys_model.vocab.operating import Operating


def _release_field_changes(
    section: str,
    subject: str,
    parts: tuple[str, ...],
    a: tuple[str, int, int],
    b: tuple[str, int, int],
) -> list[Change]:
    """A `changed` row for each of `interface`, `revision`, `version` that differs.

    `a`/`b` are each `(interface, version, revision)`, the fields `unit` and `units` diff alike.
    `revision` and `version` rows both print the release's pair through `revision_text`.
    """
    a_interface, a_version, a_revision = a
    b_interface, b_version, b_revision = b
    rows: list[Change] = []
    if a_interface != b_interface:
        rows.append(
            Change(
                section=section, change="changed", subject=subject, parts=parts, field="interface", before=a_interface, after=b_interface, detail=""
            )
        )
    if a_revision != b_revision:
        before, after = revision_text(a_version, a_revision), revision_text(b_version, b_revision)
        rows.append(Change(section=section, change="changed", subject=subject, parts=parts, field="revision", before=before, after=after, detail=""))
    if a_version != b_version:
        before, after = revision_text(a_version, a_revision), revision_text(b_version, b_revision)
        rows.append(Change(section=section, change="changed", subject=subject, parts=parts, field="version", before=before, after=after, detail=""))
    return rows


def _unit_changes(a: BaselineUnit, b: BaselineUnit) -> list[Change]:
    return _release_field_changes(
        "unit",
        a.name,
        (a.name,),
        (a.interface, a.version, a.revision),
        (b.interface, b.version, b.revision),
    )


def unit_subject_text(unit: BaselineUnit) -> str:
    """The subject of a Change on a `""` row: `<name> <V>.<R>` (model-0132; left blank)."""
    return f"{unit.name} {revision_text(unit.version, unit.revision)}"


def _by_subject[R: BaselineItem | BaselineBoundary](rows: tuple[R, ...], unit_subject: str) -> dict[str, R]:
    return {r.designation or unit_subject: r for r in rows}


def _item_field_text(field: str, value: object) -> str:
    if field in ("mpn", "manufacturer"):
        return cast("str", value)
    if field in ("installed", "external"):
        return str(value)
    # `position` is the only remaining field, `int | None`.
    return "" if value is None else str(value)


def _item_detail(row: BaselineItem) -> str:
    """The part text of an added or removed item: its set `mpn` and `manufacturer`, comma-joined."""
    return ", ".join(text for text in (row.mpn, row.manufacturer) if text)


def _item_ident(designation: str, row: BaselineItem) -> tuple[str, tuple[str, ...], str]:
    return designation, (designation,), _item_detail(row)


def _item_changes(a_rows: tuple[BaselineItem, ...], b_rows: tuple[BaselineItem, ...], unit_subject: str) -> list[Change]:
    a_index = _by_subject(a_rows, unit_subject)
    b_index = _by_subject(b_rows, unit_subject)
    changes = presence_changes("items", a_index, b_index, _item_ident)
    for designation in set(a_index) & set(b_index):
        a_row, b_row = a_index[designation], b_index[designation]
        for field in ("external", "installed", "manufacturer", "mpn", "position"):
            a_val, b_val = getattr(a_row, field), getattr(b_row, field)
            if a_val != b_val:
                before, after = _item_field_text(field, a_val), _item_field_text(field, b_val)
                changes.append(
                    Change(
                        section="items",
                        change="changed",
                        subject=designation,
                        parts=(designation,),
                        field=field,
                        before=before,
                        after=after,
                        detail="",
                    )
                )
    return sort_changes(changes)


def _nested_unit_index(
    rows: tuple[BaselineNestedUnit, ...],
) -> dict[tuple[str, str], BaselineNestedUnit]:
    index: dict[tuple[str, str], BaselineNestedUnit] = {}
    for row in rows:
        for instance in row.instances:
            index[(row.name, instance)] = row
    return index


def _nested_ident(key: tuple[str, str], _row: BaselineNestedUnit) -> tuple[str, tuple[str, ...], str]:
    name, instance = key
    return f"{name} {instance}", (instance, name), ""


def _nested_unit_changes(a_rows: tuple[BaselineNestedUnit, ...], b_rows: tuple[BaselineNestedUnit, ...]) -> list[Change]:
    a_index = _nested_unit_index(a_rows)
    b_index = _nested_unit_index(b_rows)
    changes = presence_changes("units", a_index, b_index, _nested_ident)
    for key in set(a_index) & set(b_index):
        name, instance = key
        a_row, b_row = a_index[key], b_index[key]
        changes.extend(
            _release_field_changes(
                "units",
                f"{name} {instance}",
                (instance, name),
                (a_row.interface, a_row.version, a_row.revision),
                (b_row.interface, b_row.version, b_row.revision),
            )
        )
    return sort_changes(changes)


def _boundary_ident(designation: str, row: BaselineBoundary) -> tuple[str, tuple[str, ...], str]:
    return designation, (designation,), "ports " + ", ".join(sorted(row.ports, key=natural_key))


def _boundary_changes(a_rows: tuple[BaselineBoundary, ...], b_rows: tuple[BaselineBoundary, ...], unit_subject: str) -> list[Change]:
    a_index = _by_subject(a_rows, unit_subject)
    b_index = _by_subject(b_rows, unit_subject)
    changes = presence_changes("boundary", a_index, b_index, _boundary_ident)
    for designation in set(a_index) & set(b_index):
        a_row, b_row = a_index[designation], b_index[designation]
        if a_row.ports != b_row.ports:
            a_ports, b_ports = set(a_row.ports), set(b_row.ports)
            changes.extend(
                Change(section="boundary", change="added", subject=designation, parts=(designation,), field="ports", before="", after=p, detail="")
                for p in sorted(b_ports - a_ports, key=natural_key)
            )
            changes.extend(
                Change(section="boundary", change="removed", subject=designation, parts=(designation,), field="ports", before=p, after="", detail="")
                for p in sorted(a_ports - b_ports, key=natural_key)
            )
        changes.extend(_rating_changes(designation, "rating", a_row.rating, b_row.rating))
        changes.extend(_rating_changes(designation, "operating", a_row.operating, b_row.operating))
    return sort_changes(changes)


def _field_texts(value: Rating | Operating | None) -> dict[str, str]:
    """`value`'s set fields as canonical JSON text, by field name; `{}` for `None`. A field unset or empty is absent."""
    if value is None:
        return {}
    data = cast("dict[str, JsonValue]", value_data(value))
    return {name: write_json(field, compact=True) for name, field in data.items() if field not in (None, ())}


def _rating_changes(designation: str, prefix: str, a: Rating | Operating | None, b: Rating | Operating | None) -> list[Change]:
    """One `changed` row per key of `a`/`b` that differs, field `<prefix>.<key>`."""
    a_dict, b_dict = _field_texts(a), _field_texts(b)
    return [
        Change(
            section="boundary",
            change="changed",
            subject=designation,
            parts=(designation,),
            field=f"{prefix}.{key}",
            before=a_dict.get(key, ""),
            after=b_dict.get(key, ""),
            detail="",
        )
        for key in sorted(set(a_dict) | set(b_dict))
        if a_dict.get(key) != b_dict.get(key)
    ]
