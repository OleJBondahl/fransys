"""Which items are strips, boards, racks and harnesses; the `<ref>` export-name fragments.

`strips`, `boards` are `derive.terminal_strips`, `.boards`: shared, so exports and pdf agree.
A harness is the parent of `is_cable` children (model-0026, model-0108), as `harness_cables` reads.
"""

import re
from typing import TYPE_CHECKING, Any, cast

from fransys_author import Scope

from fransys_model.derive import (
    boards,
    is_own_unit_root,
    is_plc_module,
    printed_designation,
    reference_designation,
    revision_text,
    terminal_strips,
    unit_release,
)
from fransys_model.vocab import cable_items, items, projects

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Unit

__all__ = [
    "boards",
    "export_prefix",
    "export_ref",
    "export_set_name",
    "fragment",
    "harnesses",
    "racks",
    "ref",
    "strips",
    "unit_of",
]

strips = terminal_strips

_REF_SPECIAL = re.compile(r"[+=-]")


def unit_of(handle: Scope | Id[Any], what: str, instead: str) -> Id[Unit]:
    """The unit a unit `Id` or a `Scope` made by `.unit(...)` names; refuses anything else.

    `what` names the argument in the message; `instead` is the other handle the caller accepts.
    """
    if isinstance(handle, Scope):
        if handle.unit_id is None:
            msg = (
                f"{what} needs a unit (a plain Scope, or a bare Design, is not a valid unit); "
                f"call s.unit(...) on it first, or pass {instead}"
            )
            raise TypeError(msg)
        return handle.unit_id
    if handle.kind != "unit":
        msg = f"{what} must be a unit id, not a {handle.kind!r} id"
        raise TypeError(msg)
    return cast("Id[Unit]", handle)  # the kind check above is the runtime proof


def fragment(designation: str) -> str:
    """`designation` as an export-name fragment: leading sign dropped, each `+`, `=`, `-` a `-`."""
    return _REF_SPECIAL.sub("-", designation[1:])


def ref(model: Model, item: Id[Item]) -> str:
    """The `<ref>` export-name fragment of `item`: a strip `+C1-X1` gives `C1-X1`.

    Names a per-item export in `out/all/` (`unit=None`) and a netlist intermediate.
    """
    return fragment(reference_designation(model, item))


def export_ref(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str:
    """The name fragment of `item`'s per-item export in the folder of `unit` (UNIT-ID I5).

    Unit-relative `printed_designation` through `fragment` (`-X2` gives `X2`): no parent path.
    The unit's own root gives "" (bare `connectors.csv`): its own tag is never printed in its set.
    """
    if unit is None:
        return ref(model, item)
    if is_own_unit_root(model, item, unit):
        return ""
    return fragment(printed_designation(model, item, unit=unit))


def export_set_name(model: Model, unit: Id[Unit] | None) -> str:
    """The name of `unit`'s export set (decision 0033).

    A unit's set is its release's name, the same for every instance; a system write with no Project
    has no prefix, which keeps today's names.
    """
    if unit is not None:
        return unit_release(model, unit).name
    project_table = projects(model)
    if not project_table:
        return ""
    (project,) = project_table.values()
    return project.number


def export_prefix(model: Model, unit: Id[Unit] | None) -> str:
    """`unit`'s export name prefix, `<set name>-v<V>.<R>` (decision 0033).

    A unit's prefix never depends on the Project; its version and revision come from its release.
    The system's come from the Project; empty when `export_set_name` is.
    """
    set_name = export_set_name(model, unit)
    if not set_name:
        return ""
    if unit is not None:
        release = unit_release(model, unit)
        version, revision = release.version, release.revision
    else:
        (project,) = projects(model).values()
        version, revision = project.version, project.revision
    return f"{set_name}-v{revision_text(version, revision)}"


def _parents_of(model: Model, children: set[Id[Item]]) -> tuple[Id[Item], ...]:
    all_items = items(model)
    parents: set[Id[Item]] = set()
    for child in children:
        parent = all_items[child].parent
        if parent is not None:
            parents.add(parent)
    return tuple(sorted(parents))


def harnesses(model: Model) -> tuple[Id[Item], ...]:
    """Items that are the parent of at least one cable child, `is_cable` (model decision 0026)."""
    return _parents_of(model, set(cable_items(model)))


def racks(model: Model) -> tuple[Id[Item], ...]:
    """Items that are the parent of at least one `derive.is_plc_module` child.

    A rack is read as `fransys_wago.modules_xml` reads it, through `plc_rack_modules`.
    """
    return _parents_of(
        model, {item.id for item in items(model).values() if is_plc_module(model, item)}
    )
