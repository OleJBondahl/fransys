"""The release manifest (`baseline/manifest.json`, baseline spec L3): its fields and its text."""

import hashlib
import importlib.metadata
from typing import TYPE_CHECKING, Any, cast

from fransys_model.derive import (
    baseline,
    current_revision,
    document_unit,
    function_designation,
    numbering_pins,
    port_designation,
    unit_items,
    unit_release,
    unit_subtree,
    units,
)
from fransys_model.kernel import Finding, Id, JsonValue, Severity, key_text, write_json
from fransys_model.vocab import documents, functions, items, part_libraries, ports, projects
from fransys_model.vocab import parts as model_parts

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab import Function, Item
    from fransys_model.vocab import Unit as ModelUnit

# Every workspace package's own distribution name (root `pyproject.toml`'s `[tool.uv.workspace]
# members`, confirmed): the manifest's `packages` list (baseline spec L3).
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


def _instance_tag(model: Model, child: Id[ModelUnit]) -> str | None:
    """The instance's tag: the written one, else the numbering pass's (`numbering_pins` row)."""
    record = units(model)[child]
    if record.tag is not None:
        return record.tag
    if record.parent is None:
        return None
    key = numbering_pins.unit_position(model, child)[0]
    rows = numbering_pins.pins(model, record.parent).items
    return next((row.text for row in rows if row.key == key), None)


def _relative_key(model: Model, unit: Id[ModelUnit] | None, subject: Id[ModelUnit]) -> str:
    """`subject`'s key below `unit` (below its own parent when it is `unit` or `unit` is `None`)."""
    key = units(model)[subject].key
    if unit is None or unit == subject:
        return "/".join(numbering_pins.unit_position(model, subject)[0])
    return "/".join(key[len(units(model)[unit].key) - 1 :])


def _instance_text(model: Model, unit: Id[ModelUnit] | None, subject: Id[ModelUnit]) -> str:
    """The listing's text for instance `subject` from `unit`: `-U1-U3`; a link untagged: its key."""
    chain: list[Id[ModelUnit]] = []
    current: Id[ModelUnit] | None = subject
    while current is not None and current != unit:
        chain.append(current)
        current = units(model)[current].parent
    tags = [_instance_tag(model, link) for link in reversed(chain)]
    texts = [tag for tag in tags if tag is not None]
    if not tags or len(texts) < len(tags):
        return _relative_key(model, unit, subject)
    return "-" + "-".join(texts)


def _subject_text(model: Model, unit: Id[ModelUnit] | None, subject: Id[Any]) -> str:
    """`subject` as a designation relative to `unit`; a unit is `_instance_text`, a `Net` its key.

    No `SchemaError` guard: HARNESS_WITHOUT_TAG (model-0107) makes the refusing shape an ERROR,
    and `_manifest` runs only after release's ERROR gate.
    """
    if subject.kind == "item":
        return baseline.unit_designation(model, unit, cast("Id[Item]", subject))
    if subject.kind == "function":
        function_id: Id[Function] = cast("Id[Function]", subject)
        return function_designation(model, function_id, unit=unit)
    if subject.kind == "port":
        return port_designation(model, subject, unit=unit)
    if subject.kind == "unit":
        return _instance_text(model, unit, cast("Id[ModelUnit]", subject))
    return key_text(model.tables[subject.kind][subject])


_OWNED_KINDS = frozenset({"item", "function", "port", "unit", "document"})


def _unit_subject_ids(model: Model, unit: Id[ModelUnit]) -> frozenset[Id[Any]]:
    """Every id `unit` owns: its subtree's items, functions, ports, units and its documents."""
    item_ids = unit_items(model, unit)
    function_ids = {fid for fid, fn in functions(model).items() if fn.item in item_ids}
    port_ids = {pid for pid, port in ports(model).items() if port.function in function_ids}
    document_ids = {i for i, r in documents(model).items() if document_unit(model, r) == unit}
    return frozenset(item_ids) | function_ids | port_ids | unit_subtree(model, unit) | document_ids


def _concerns(finding: Finding, owned: frozenset[Id[Any]]) -> bool:
    """Rule D (decision 0104): any subject of an owned kind is inside, or none is of one."""
    kinded = [s for s in finding.subjects if s.kind in _OWNED_KINDS]
    return not kinded or any(s in owned for s in kinded)


def _warning_entries(
    model: Model, unit: Id[ModelUnit] | None, findings: tuple[Finding, ...]
) -> list[JsonValue]:
    """Every `WARNING` of `findings` that concerns `unit` (`None` is the system: all of them).

    `message` is the raw pre-`describe` text, never the resolved one.
    """
    owned = None if unit is None else _unit_subject_ids(model, unit)
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
    """The installed version of every Fransys workspace package (manifest L3)."""
    return [
        {"name": name, "version": importlib.metadata.version(name)}
        for name in sorted(_WORKSPACE_PACKAGES)
    ]


def _part_library_versions(model: Model, unit: Id[ModelUnit] | None) -> list[JsonValue]:
    """The distinct `(name, version)` of every part library behind `unit`'s items.

    `None` is every item. A unit uses the whole subtree (`unit_items`), broader than L2's listing.
    """
    item_ids = items(model).keys() if unit is None else unit_items(model, unit)
    all_items = items(model)
    all_parts = model_parts(model)
    all_libraries = part_libraries(model)
    found = set()
    for item_id in item_ids:
        part_id = all_items[item_id].part
        if part_id is None:
            continue
        library_id = all_parts[part_id].library
        if library_id is None:
            continue
        library = all_libraries[library_id]
        found.add((library.name, library.version))
    return [{"name": name, "version": version} for name, version in sorted(found)]


def _tool_versions() -> dict[str, JsonValue]:
    """`typst`'s own version; no release spawns Graphviz or `wireviz` any more (CT1)."""
    return {"typst": importlib.metadata.version("typst")}


def _nested_entries(model: Model, unit: Id[ModelUnit] | None) -> list[JsonValue]:
    """Every release nested in `unit`'s subtree (`None`: every unit in the model), one row each.

    Two instances of one release give the same listing digest, so rows dedupe by
    `(name, version, revision, listing_digest)`.
    """
    nested_ids: tuple[Id[ModelUnit], ...] = (
        tuple(sorted(units(model)))
        if unit is None
        else tuple(sorted(unit_subtree(model, unit) - {unit}))
    )
    found = set()
    for nested_id in nested_ids:
        release = unit_release(model, nested_id)
        digest = hashlib.sha256(
            baseline.dumps(baseline.listing(model, nested_id)).encode("utf-8")
        ).hexdigest()
        found.add((release.name, release.version, release.revision, digest))
    return [
        {"name": name, "version": version, "revision": revision, "listing_digest": digest}
        for name, version, revision, digest in sorted(found)
    ]


def _unit_manifest_fields(
    model: Model, unit: Id[ModelUnit] | None
) -> tuple[dict[str, JsonValue], dict[str, JsonValue] | None]:
    """`(unit, history)` of the manifest (L3): the release's or the project's own facts."""
    if unit is not None:
        release_record = unit_release(model, unit)
        unit_dict: dict[str, JsonValue] = {
            "name": release_record.name,
            "version": release_record.version,
            "revision": release_record.revision,
            "interface": release_record.interface,
        }
        entry = current_revision(model, release=release_record.id)
    else:
        project = next(iter(projects(model).values()))
        unit_dict = {
            "name": project.number,
            "version": project.version,
            "revision": project.revision,
            "interface": "",
        }
        entry = current_revision(model, release=None)
    history: dict[str, JsonValue] | None = (
        None
        if entry is None
        else {
            "date": entry.date,
            "text": entry.text,
            "created": entry.created,
            "checked": entry.checked,
            "approved": entry.approved,
        }
    )
    return unit_dict, history


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
    unit_dict, history = _unit_manifest_fields(model, unit)
    listing_digest = hashlib.sha256(baseline_files["baseline/listing.json"]).hexdigest()
    files_entries: list[JsonValue] = [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted((*exports.items(), *baseline_files.items()), key=lambda f: f[0])
    ]
    data: dict[str, JsonValue] = {
        "listing_digest": listing_digest,
        "model_digest": model.digest,
        "unit": unit_dict,
        "history": history,
        "packages": _package_versions(),
        "part_libraries": _part_library_versions(model, unit),
        "tool_versions": _tool_versions(),
        "warnings": _warning_entries(model, unit, raw_findings),
        "nested": _nested_entries(model, unit),
        "files": files_entries,
    }
    return write_json(data, compact=True) + "\n"
