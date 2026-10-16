"""The release manifest (`baseline/manifest.json`): its fields and its text."""

import dataclasses
import hashlib
import importlib.metadata
from typing import TYPE_CHECKING, Any, cast

from fransys_model.derive import (
    baseline,
    function_designation,
    is_unit_owned_kind,
    manifest_rows,
    numbering_pins,
    port_designation,
    record_key_text,
    subject_kind,
    unit_chain_below,
    unit_key,
    unit_owned_ids,
)
from fransys_model.kernel import Finding, Id, JsonValue, Severity, write_json
from fransys_model.vocab import SubjectKind

from ._release_reader import BASELINE_FILES

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab import Function, Item
    from fransys_model.vocab import Unit as ModelUnit

# Every workspace package's own distribution name (root `pyproject.toml`'s `[tool.uv.workspace]
# members`, confirmed): the manifest's `packages` list.
_WORKSPACE_PACKAGES = (
    "fransys",
    "fransys-model",
    "electrical-symbols",
    "fransys-parts",
    "fransys-author",
    "fransys-layout",
    "fransys-render",
    "fransys-reports",
    "fransys-pdf",
    "fransys-kicad",
    "fransys-wago",
    "fransys-overview",
)


def _relative_key(model: Model, unit: Id[ModelUnit] | None, subject: Id[ModelUnit]) -> str:
    """`subject`'s key below `unit` (below its own parent when it is `unit` or `unit` is `None`)."""
    key = unit_key(model, subject)
    if unit is None or unit == subject:
        return "/".join(numbering_pins.unit_position(model, subject)[0])
    return "/".join(key[len(unit_key(model, unit)) - 1 :])


def _instance_text(model: Model, unit: Id[ModelUnit] | None, subject: Id[ModelUnit]) -> str:
    """The listing's text for instance `subject` from `unit`: `-U1-U3`; a link untagged: its key."""
    chain = unit_chain_below(model, unit, subject)
    tags = [numbering_pins.unit_tag(model, link) for link in reversed(chain)]
    texts = [tag for tag in tags if tag is not None]
    if not tags or len(texts) < len(tags):
        return _relative_key(model, unit, subject)
    return numbering_pins.instance_name(texts)


def _subject_text(model: Model, unit: Id[ModelUnit] | None, subject: Id[Any]) -> str:
    """`subject` as a designation relative to `unit`; a unit is `_instance_text`, a `Net` its key.

    No `SchemaError` guard: HARNESS_WITHOUT_TAG (model-0107) makes the refusing shape an ERROR,
    and `_manifest` runs only after release's ERROR gate.
    """
    kind = subject_kind(subject)
    if kind is SubjectKind.ITEM:
        return baseline.unit_designation(model, unit, cast("Id[Item]", subject))
    if kind is SubjectKind.FUNCTION:
        function_id: Id[Function] = cast("Id[Function]", subject)
        return function_designation(model, function_id, unit=unit)
    if kind is SubjectKind.PORT:
        return port_designation(model, subject, unit=unit)
    if kind is SubjectKind.UNIT:
        return _instance_text(model, unit, cast("Id[ModelUnit]", subject))
    return record_key_text(model, subject)


def _concerns(finding: Finding, owned: frozenset[Id[Any]]) -> bool:
    """Rule D (decision 0104): any subject of an owned kind is inside, or none is of one."""
    kinded = [s for s in finding.subjects if is_unit_owned_kind(s)]
    return not kinded or any(s in owned for s in kinded)


def _warning_entries(
    model: Model, unit: Id[ModelUnit] | None, findings: tuple[Finding, ...]
) -> list[JsonValue]:
    """Every `WARNING` of `findings` that concerns `unit` (`None` is the system: all of them).

    `message` is the raw pre-`describe` text, never the resolved one.
    """
    owned = None if unit is None else unit_owned_ids(model, unit)
    selected = sorted(
        (
            finding
            for finding in findings
            if finding.severity is Severity.WARNING and (owned is None or _concerns(finding, owned))
        ),
        key=lambda finding: (finding.code, finding.message),
    )
    return [
        {
            "code": finding.code,
            "subjects": [_subject_text(model, unit, s) for s in finding.subjects],
            "message": finding.message,
        }
        for finding in selected
    ]


def _package_versions() -> list[JsonValue]:
    """The installed version of every Fransys workspace package."""
    return [
        {"name": name, "version": importlib.metadata.version(name)}
        for name in sorted(_WORKSPACE_PACKAGES)
    ]


def _tool_versions() -> dict[str, JsonValue]:
    """`typst`'s own version; no release spawns Graphviz or `wireviz` any more."""
    return {"typst": importlib.metadata.version("typst")}


def _manifest(
    model: Model,
    unit: Id[ModelUnit] | None,
    *,
    exports: dict[str, bytes],
    baseline_files: dict[str, bytes],
    raw_findings: tuple[Finding, ...],
) -> str:
    """`baseline/manifest.json`'s canonical JSON text; the listing digest is read off the bytes.

    `baseline_files` holds the other baseline files (`listing.json`, `model.json`, and for a unit
    `numbering.json`, `changes.md`, `changes.csv`); their paths and hashes join `files`.
    """
    rows = manifest_rows(model, unit)
    listing_digest = hashlib.sha256(baseline_files[BASELINE_FILES["listing"]]).hexdigest()
    files_entries: list[JsonValue] = [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted((*exports.items(), *baseline_files.items()), key=lambda f: f[0])
    ]
    data: dict[str, JsonValue] = {
        "listing_digest": listing_digest,
        "model_digest": model.digest,
        "unit": dataclasses.asdict(rows.identity),
        "history": None if rows.entry is None else dataclasses.asdict(rows.entry),
        "packages": _package_versions(),
        "part_libraries": [dataclasses.asdict(r) for r in rows.part_libraries],
        "tool_versions": _tool_versions(),
        "warnings": _warning_entries(model, unit, raw_findings),
        "nested": [dataclasses.asdict(r) for r in rows.nested],
        "files": files_entries,
    }
    return write_json(data, compact=True) + "\n"
