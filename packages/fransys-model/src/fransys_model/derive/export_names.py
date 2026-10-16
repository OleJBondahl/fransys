"""The one home of the file name each export gets (decision 0033, root 0117, root 0185).

A function of the model alone, so `write` and the overview page name a file the same way.
"""

import re

from fransys_model.vocab.enums import DocumentPreset
from fransys_model.vocab.tables import projects
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit
lazy from fransys_model.vocab.document import Document

from .designation import (
    is_own_unit_root,
    location_node_designation,
    printed_designation,
    reference_designation,
)
from .document_unit import document_unit
from .release_identity import release_identity
from .revision_text import revision_text

__all__ = [
    "document_export_name",
    "export_fragment",
    "export_name",
    "export_prefix",
    "export_ref",
    "export_set_name",
    "reference_fragment",
]

_REF_SPECIAL = re.compile(r"[+=-]")


def export_fragment(designation: str) -> str:
    """`designation` as an export-name fragment: leading sign dropped, each `+`, `=`, `-` a `-`."""
    return _REF_SPECIAL.sub("-", designation[1:])


def reference_fragment(model: Model, item: Id[Item]) -> str:
    """The `<ref>` export-name fragment of `item`: a strip `+C1-X1` gives `C1-X1`.

    Names a per-item export in `out/all/` (`unit=None`) and a netlist intermediate.
    """
    return export_fragment(reference_designation(model, item))


def export_ref(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str:
    """The name fragment of `item`'s per-item export in the folder of `unit`.

    Unit-relative `printed_designation` through `export_fragment` (`-X2` gives `X2`): no parent
    path. The unit's own root gives "" (bare `connectors.csv`): its own tag is never printed in
    its set.
    """
    if unit is None:
        return reference_fragment(model, item)
    if is_own_unit_root(model, item, unit):
        return ""
    return export_fragment(printed_designation(model, item, unit=unit))


def export_set_name(model: Model, unit: Id[Unit] | None) -> str:
    """The name of `unit`'s export set.

    A unit's set is its release's name, the same for every instance; a system write with no Project
    has no prefix, which keeps today's names.
    """
    if unit is None and not projects(model):
        return ""
    return release_identity(model, unit).name


def export_prefix(model: Model, unit: Id[Unit] | None) -> str:
    """`unit`'s export name prefix, `<set name>-v<V>.<R>`.

    A unit's prefix never depends on the Project; its version and revision come from its release.
    The system's come from the Project; empty when `export_set_name` is.
    """
    set_name = export_set_name(model, unit)
    if not set_name:
        return ""
    identity = release_identity(model, unit)
    return f"{set_name}-v{revision_text(identity.version, identity.revision)}"


def export_name(
    model: Model,
    unit: Id[Unit] | None,
    extension: str,
    *,
    kind: str | None = None,
    fragment: str | None = None,
) -> str:
    """`<prefix>[-<kind>][-<fragment>].<extension>`; an empty part is left out.

    The one place prefix, kind and fragment are joined; the prefix is `export_prefix`.
    """
    joined = "-".join(part for part in (export_prefix(model, unit), kind, fragment) if part)
    return f"{joined}.{extension}"


def document_export_name(model: Model, unit: Id[Unit] | None, record: Document) -> str:
    """One document's PDF name, from its own subject, never its cover.

    Unit subject (`record.unit`, or `record.unit_name` via `document_unit`): its own prefix.
    Location, item, SYSTEM: the write scope's; empty prefix gives bare `<cover-stem>.pdf` here.
    """
    document_own_unit = document_unit(model, record)
    if document_own_unit is not None:
        kind = "harness" if record.preset is DocumentPreset.HARNESS_DRAWING else None
        return export_name(model, document_own_unit, "pdf", kind=kind)
    if not export_prefix(model, unit):
        return export_name(model, unit, "pdf", fragment=record.key[1])
    if record.location is not None:
        fragment = export_fragment(location_node_designation(model, record.location))
        return export_name(model, unit, "pdf", fragment=fragment)
    if record.item is not None:
        return export_name(model, unit, "pdf", fragment=export_ref(model, record.item, unit))
    return export_name(model, unit, "pdf")
