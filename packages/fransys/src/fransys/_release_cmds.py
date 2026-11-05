"""The release commands: `release`, `diff`, `verify`, `rebaseline`."""

import dataclasses
import shutil
import tempfile
from pathlib import Path

from fransys_reports import (
    changes_markdown,
)

from fransys_model.derive import (
    baseline,
    errors_of,
    gone_or_moved,
    has_project,
    numbering_pins,
    unit_ids,
)
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.kernel import (
    Finding,
    Id,
    Model,
)
from fransys_model.kernel import dumps as model_dumps
lazy from fransys_model.derive.baseline import Listing
lazy from fransys_model.vocab import Unit as ModelUnit

from . import _revision_pins
from ._baseline_findings import baseline_findings
from ._export_ledger import changes_csv_file
from ._exports import _Export, _exports, _put, _resolve_unit
from ._rebaseline import plan_rebaseline, write_plan
from ._release_checks import (
    _l4_findings,
    _pin_source,
    _previous_release_listing,
    _release_target,
    _ReleaseTarget,
    _since_listing,
)
from ._release_files import release_file_findings
from ._release_manifest import _manifest
from ._release_reader import BASELINE_FILES, stored_listing
from .pipeline import BuildFailedError, BuildResult, _Drawn, _library, _raw_findings, _resolved, _result_svgs


def release(result: BuildResult, into: Path, *, unit: object = None) -> Path:
    """Output: release a unit, or the system, as a frozen baseline under `into`.

    Writes `<into>/<name>/<version>.<revision>/`: the unit's exports as `write` makes them,
    `baseline/` (listing, model, manifest) and, after a first release, `changes.md` and
    `changes.csv`. Runs the same gate as `write` plus the release checks: any `ERROR`
    raises `BuildFailedError` and writes nothing. An identical stored listing text returns the
    existing path untouched. Files are built in a temporary sibling and renamed, so a failure
    leaves nothing behind.

    Does not release when `check` finds an ERROR; does not overwrite an identical release.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    svgs = _result_svgs(result)
    raw_findings = _gate(result, resolved_unit, into, svgs)
    target_info = _release_target(model, resolved_unit, into)
    target = target_info.path
    new_listing = baseline.listing(model, resolved_unit)
    stored_text = stored_listing(target)
    if stored_text is not None and baseline.matches(stored_text, new_listing):
        return target
    exports = _exports(_Export(_Drawn(model, result.drawings, result.diagrams, _library(result), svgs), result.settings, resolved_unit))
    baseline_files = _baseline_files(model, resolved_unit, target_info, into, new_listing)
    manifest_text = _manifest(model, resolved_unit, exports=exports, baseline_files=baseline_files, raw_findings=raw_findings)
    _publish(target, (*exports.items(), *baseline_files.items()), manifest_text)
    return target


def _gate(result: BuildResult, resolved_unit: Id[ModelUnit] | None, into: Path, svgs: dict[str, str]) -> tuple[Finding, ...]:
    """Raise `BuildFailedError` on any ERROR; else return the raw findings the manifest records."""
    model = result.model
    l4 = name_findings(model, _l4_findings(model, resolved_unit, into))
    raw_findings = _revision_pins.with_warnings(_raw_findings(result, svgs), l4)
    errors = errors_of((*_resolved(raw_findings, model), *l4))
    if errors:
        raise BuildFailedError(errors, model=model)
    return raw_findings


def _baseline_files(
    model: Model, resolved_unit: Id[ModelUnit] | None, target_info: _ReleaseTarget, into: Path, new_listing: Listing
) -> dict[str, bytes]:
    """The `baseline/` files of a release: listing, model, numbering and, after a first release, the changes."""
    files = {
        BASELINE_FILES["listing"]: baseline.dumps(new_listing).encode("utf-8"),
        BASELINE_FILES["model"]: model_dumps(model).encode("utf-8"),
    }
    if resolved_unit is not None:
        current_numbering = numbering_pins.pins(model, resolved_unit)
        pin_source = _pin_source(target_info, into)
        retired = () if pin_source is None else gone_or_moved(pin_source[1], current_numbering.items)
        files[BASELINE_FILES["numbering"]] = numbering_pins.dumps(dataclasses.replace(current_numbering, retired=retired)).encode("utf-8")
    previous_listing = _previous_release_listing(target_info)
    if previous_listing is not None:
        listing_diff = baseline.diff(previous_listing, new_listing)
        files[BASELINE_FILES["changes_md"]] = changes_markdown(listing_diff).encode("utf-8")
        files.update(changes_csv_file(model, listing_diff))
    return files


def _publish(target: Path, files: tuple[tuple[str, bytes], ...], manifest_text: str) -> None:
    """Build the release in a temporary sibling of `target` and rename it, leaving nothing on failure."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=target.parent, prefix=".release-"))
    built = False
    try:
        (tmp_dir / "baseline").mkdir()
        for filename, data in files:
            _put(tmp_dir / filename, data)
        (tmp_dir / BASELINE_FILES["manifest"]).write_bytes(manifest_text.encode("utf-8"))
        tmp_dir.rename(target)
        built = True
    finally:
        if not built:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def diff(result: BuildResult, baselines: Path, *, unit: object = None, against: str | None = None) -> str:
    """Output: return the Markdown change list from a stored release to the model as it stands now.

    By default `a` is the release stored at the model's current revision, else the previous
    released revision; `against="1.3"` names a sibling `<version>.<revision>` folder directly.
    `unit` resolves as in `release`. Raises `FileNotFoundError` when no release is found,
    `TypeError` or `ValueError` for a bad `unit`.

    Does not write files; does not guess a release by likeness.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    b = baseline.listing(model, resolved_unit)
    target_info = _release_target(model, resolved_unit, baselines)
    a = _listing_against(target_info, against)
    return changes_markdown(baseline.diff(a, b))


def _listing_against(target_info: _ReleaseTarget, against: str | None) -> Listing:
    """The stored listing to diff from: the sibling `against`, else the since-listing."""
    parent = target_info.path.parent
    if against is not None:
        candidate = parent / against
        text = stored_listing(candidate)
        if text is None:
            msg = f"no release found at {candidate}"
            raise FileNotFoundError(msg)
        return baseline.loads(text)
    since = _since_listing(target_info)
    if since is None:
        msg = f"no released revision found under {parent}"
        raise FileNotFoundError(msg)
    return since


def verify(result: BuildResult, baselines: Path) -> tuple[Finding, ...]:
    """Output: return one `BASELINE_DIFFERS` `ERROR` per unit instance, or the system, that drifted.

    Compares the rebuilt listing with the stored one under `baselines`, for every unit and for the
    system when the model holds a `Project`, under the rules of the `fransys` that cut it: a rule
    that moved since gives `BASELINE_RULES_MOVED` (INFO), one too old to know `BASELINE_TOO_OLD`.
    The model digest is never compared.
    Also re-hashes every release file: `RELEASE_FILE_CHANGED`, `RELEASE_FILE_MISSING`.
    Meant for a consumer's test, wherever they want it.

    Does not write files, release or gate `write`; does not report a unit with no stored baseline.
    """
    model = result.model
    subjects: tuple[Id[ModelUnit] | None, ...] = (
        *unit_ids(model),
        *((None,) if has_project(model) else ()),
    )
    findings: list[Finding] = []
    for unit in subjects:
        target = _release_target(model, unit, baselines)
        stored_text = stored_listing(target.path)
        if stored_text is None:
            continue
        findings.extend(baseline_findings(model, unit, target, stored_text, nested=False))
    findings.extend(release_file_findings(baselines))
    return tuple(findings)


def rebaseline(result: BuildResult, baselines: Path, *, unit: str | Id[ModelUnit] | None = None) -> tuple[Path, ...]:
    """Output: re-cut every stored baseline the current rules print differently, once.

    Rewrites `baseline/listing.json` and `baseline/manifest.json` of each release under
    `baselines` that `verify` notes with `BASELINE_RULES_MOVED` or `BASELINE_ROWS_UNCHECKED`,
    children before parents, and returns those folders (`()` when nothing moved). The manifest
    keeps the old digest, listing version and `fransys` in a `rebaselined` record. `unit=None`
    covers every unit and the system with a stored baseline; a unit covers it and the units below.
    Raises `BuildFailedError` and writes nothing when a real row changed (`BASELINE_DIFFERS`), a
    baseline is too old, or a release file is not as released.

    Does not write an export, `model.json` or `numbering.json`.
    """
    model = result.model
    plan = plan_rebaseline(model, baselines, _resolve_unit(model, unit))
    if plan.findings:
        raise BuildFailedError(_resolved(plan.findings, model), model=model)
    return write_plan(plan)
