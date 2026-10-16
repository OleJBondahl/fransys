"""`fr.rebaseline`: re-cut stored baselines under today's rules, exports untouched (LS4, root-0214).

`plan_rebaseline` reads and compares, writes nothing, and gives every refusal at once.
`write_plan` then rewrites only `baseline/listing.json` and `baseline/manifest.json` of each
release folder, children before parents, each file atomically.
"""

import dataclasses
import hashlib
import importlib.metadata
import json
from typing import Any
lazy from pathlib import Path

from fransys_model.derive import baseline, rebaseline_subjects
from fransys_model.kernel import Finding, Id, JsonValue, Model, write_json
lazy from fransys_model.vocab import Unit as ModelUnit

from ._baseline_findings import status_findings
from ._release_checks import _release_target
from ._release_files import release_file_findings
from ._release_reader import (
    BASELINE_FILES,
    manifest_data,
    manifest_path,
    read_release,
    stored_fransys_version,
    stored_listing,
)

_Key = tuple[str, int, int]


@dataclasses.dataclass(frozen=True, slots=True)
class _Pin:
    """A nested pin of a parent's manifest that takes a re-cut child's new listing digest."""

    key: _Key
    digest: str


@dataclasses.dataclass(frozen=True, slots=True)
class _Rewrite:
    """One folder to rewrite: its new listing text (`None`: only pins move) and its old values."""

    folder: Path
    listing_text: str | None
    old_version: int
    old_digest: str
    old_fransys: str
    unchecked: int
    pins: tuple[_Pin, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Plan:
    """What `plan_rebaseline` found: the rewrites in write order, or the findings that refuse."""

    rewrites: tuple[_Rewrite, ...]
    findings: tuple[Finding, ...]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pins(folder: Path, moved: dict[_Key, str]) -> tuple[_Pin, ...]:
    """The nested pins of `folder` that name a release in `moved` with another digest."""
    if not moved:
        return ()
    pins = read_release(folder).nested
    keyed = (((p.name, p.version, p.revision), p.listing_digest) for p in pins)
    return tuple(_Pin(key, moved[key]) for key, digest in keyed if moved.get(key, digest) != digest)


def _plan_one(
    model: Model, unit: Id[ModelUnit] | None, baselines: Path, moved: dict[_Key, str]
) -> tuple[_Rewrite | None, tuple[Finding, ...]]:
    target = _release_target(model, unit, baselines)
    stored = stored_listing(target.path)
    if stored is None:
        return None, ()
    version = stored_fransys_version(target.path) or ""
    status = baseline.listing_status(stored, model, unit, version)
    if status.state in ("differs", "too_old"):
        return None, status_findings(status, unit, target, nested=False)
    text = None if status.state == "same" else baseline.dumps(baseline.listing(model, unit))
    pins = _pins(target.path, moved)
    if text is None and not pins:
        return None, ()
    if text is not None:
        moved[(target.name, target.version, target.revision)] = _digest(text)
    old = (json.loads(stored)["listing_version"], read_release(target.path).listing_digest)
    return _Rewrite(target.path, text, *old, version, status.unchecked, pins), ()


def plan_rebaseline(model: Model, baselines: Path, unit: Id[ModelUnit] | None) -> Plan:
    """Every rewrite `baselines` needs under today's rules, or every finding that refuses.

    A real change, a baseline too old to know or a release file not as released refuses the whole
    call; a unit with no stored baseline is skipped, as `verify` skips it.
    """
    if broken := release_file_findings(baselines):
        return Plan((), broken)
    moved: dict[_Key, str] = {}
    rewrites: dict[Path, _Rewrite] = {}
    found: list[Finding] = []
    for subject in rebaseline_subjects(model, unit):
        rewrite, problems = _plan_one(model, subject, baselines, moved)
        found.extend(problems)
        if rewrite is not None:
            rewrites.setdefault(rewrite.folder, rewrite)
    return Plan((), tuple(found)) if found else Plan(tuple(rewrites.values()), ())


def _records(rewrite: _Rewrite) -> list[JsonValue]:
    """The `rebaselined` records one rewrite adds: the old values, a reason, the child, the count.

    `cut_by` is the `fransys` whose rules the new listing holds (`None` on a `nested` record).
    """
    old: dict[str, JsonValue] = {
        "listing_version": rewrite.old_version,
        "listing_digest": rewrite.old_digest,
        "fransys": rewrite.old_fransys,
    }
    rows: list[JsonValue] = []
    if rewrite.listing_text is not None:
        rows.append(
            {
                **old,
                "reason": "rules",
                "unit": None,
                "unchecked_rows": rewrite.unchecked,
                "cut_by": importlib.metadata.version("fransys"),
            }
        )
    rows.extend(
        {**old, "reason": "nested", "unit": pin.key[0], "unchecked_rows": 0, "cut_by": None}
        for pin in rewrite.pins
    )
    return rows


def _edited(manifest: dict[str, Any], rewrite: _Rewrite) -> dict[str, Any]:
    """`manifest` with the new listing digest, the moved pins and the `rebaselined` records."""
    if rewrite.listing_text is not None:
        digest = _digest(rewrite.listing_text)
        manifest["listing_digest"] = digest
        for row in manifest["files"]:
            if row["path"] == BASELINE_FILES["listing"]:
                row["sha256"] = digest
    for pin in rewrite.pins:
        for row in manifest["nested"]:
            if (row["name"], row["version"], row["revision"]) == pin.key:
                row["listing_digest"] = pin.digest
    manifest.setdefault("rebaselined", []).extend(_records(rewrite))
    return manifest


def _replace(path: Path, data: bytes) -> None:
    """Write `data` to `path` through a temp file in the same folder and `os.replace`."""
    temp = path.with_name(f"{path.name}.rebaseline")
    temp.write_bytes(data)
    temp.replace(path)


def _apply(rewrite: _Rewrite) -> None:
    """Rewrite one folder; a stop between its two files leaves listing.json off the manifest."""
    manifest = _edited(manifest_data(rewrite.folder), rewrite)
    text = write_json(manifest, compact=True) + "\n"
    _replace(manifest_path(rewrite.folder), text.encode("utf-8"))
    if rewrite.listing_text is not None:
        _replace(rewrite.folder / BASELINE_FILES["listing"], rewrite.listing_text.encode("utf-8"))


def write_plan(plan: Plan) -> tuple[Path, ...]:
    """Apply `plan`'s rewrites in order; the folders rewritten, `()` when there are none."""
    for rewrite in plan.rewrites:
        _apply(rewrite)
    return tuple(rewrite.folder for rewrite in plan.rewrites)
