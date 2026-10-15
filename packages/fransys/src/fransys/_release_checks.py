"""The release identity and the checks `release`, `diff`, `verify` and `write` share.

`_release_target` computes `<into>/<name>/<version>.<revision>/` once; the L4 checks read it.
"""

import dataclasses
from typing import TYPE_CHECKING
lazy from pathlib import Path

from fransys_model.derive import (
    baseline,
    current_revision,
    numbering_pins,
    release_order,
    revision_text,
    same_version,
    unit_release,
    unit_subtree,
    units,
)
from fransys_model.kernel import Finding, Id, Severity
from fransys_model.vocab import projects
lazy from fransys_model.derive.numbering_pins import NumberingPins

from . import _revision_pins
from ._baseline_cause import sections_text
from ._history_gate import history_findings
from ._release_reader import listed_siblings, stored_listing, stored_numbering

if TYPE_CHECKING:
    from fransys_model.derive.baseline import Listing, ListingDiff
    from fransys_model.kernel import Model
    from fransys_model.vocab import Unit as ModelUnit


@dataclasses.dataclass(frozen=True, slots=True)
class _ReleaseTarget:
    """A unit's, or the system's, release identity and target directory.

    Bundles `_release_target`'s result so `release` and every `_l4_findings` check pass one value.
    """

    name: str
    version: int
    revision: int
    path: Path


def _release_target(model: Model, unit: Id[ModelUnit] | None, into: Path) -> _ReleaseTarget:
    """A unit's, or the system's, release name, version, revision and target directory.

    The one place `<into>/<name>/<version>.<revision>/` is computed; `release`, `_l4_findings` call.
    """
    if unit is not None:
        release_record = unit_release(model, unit)
        name = release_record.name
        version, revision = release_record.version, release_record.revision
    else:
        project = next(iter(projects(model).values()))
        name = project.number
        version, revision = project.version, project.revision
    path = into / name / revision_text(version, revision)
    return _ReleaseTarget(name=name, version=version, revision=revision, path=path)


def _revision_already_released_finding(
    model: Model, unit: Id[ModelUnit] | None, release: _ReleaseTarget
) -> Finding | None:
    """`REVISION_ALREADY_RELEASED`: `release.path` already holds a differing listing.

    Applies to a unit and the system (`unit=None`, `subjects=()`): a released folder never changes.
    """
    stored_text = stored_listing(release.path)
    new_listing = baseline.listing(model, unit)
    if stored_text is None or baseline.matches(stored_text, new_listing):
        return None
    stored = baseline.loads(stored_text)
    sections = ", ".join(baseline.differing_sections(stored, new_listing))
    return Finding(
        code="REVISION_ALREADY_RELEASED",
        severity=Severity.ERROR,
        subjects=(unit,) if unit is not None else (),
        message=(
            f"{release.name} {revision_text(release.version, release.revision)} is already "
            f"released and differs in: {sections}"
        ),
    )


def _baseline_differs_finding(
    model: Model, unit: Id[ModelUnit] | None, release: _ReleaseTarget, stored_text: str
) -> Finding | None:
    """`BASELINE_DIFFERS` when `stored_text` differs from `unit`'s fresh listing.

    The one comparison `_nested_release_findings` and `verify` share; `stored_text` is not `None`.
    The caller decides what no stored baseline means; this only answers whether it differs.
    """
    new_listing = baseline.listing(model, unit)
    if baseline.matches(stored_text, new_listing):
        return None
    sections = sections_text(baseline.loads(stored_text), new_listing)
    release_revision_text = revision_text(release.version, release.revision)
    return Finding(
        code="BASELINE_DIFFERS",
        severity=Severity.ERROR,
        subjects=(unit,) if unit is not None else (),
        message=(
            f"{release.name} {release_revision_text} differs from its released baseline in: "
            f"{sections}"
        ),
    )


def _nested_release_findings(model: Model, unit: Id[ModelUnit] | None, into: Path) -> list[Finding]:
    """`RELEASE_NESTED_UNRELEASED` and `BASELINE_DIFFERS`: the whole subtree, any depth."""
    nested_ids: tuple[Id[ModelUnit], ...] = (
        tuple(sorted(units(model)))
        if unit is None
        else tuple(sorted(unit_subtree(model, unit) - {unit}))
    )
    findings: list[Finding] = []
    for nested in nested_ids:
        nested_release = _release_target(model, nested, into)
        nested_stored_text = stored_listing(nested_release.path)
        if nested_stored_text is None:
            nested_revision_text = revision_text(nested_release.version, nested_release.revision)
            findings.append(
                Finding(
                    code="RELEASE_NESTED_UNRELEASED",
                    severity=Severity.ERROR,
                    subjects=(nested,),
                    message=(
                        f"{nested_release.name} {nested_revision_text}, nested in this "
                        "release, has not been released"
                    ),
                )
            )
            continue
        differs = _baseline_differs_finding(model, nested, nested_release, nested_stored_text)
        if differs is not None:
            findings.append(differs)
    return findings


def _previous_release_listing(release: _ReleaseTarget) -> Listing | None:
    """The stored listing of the highest release ordered below this one, or `None`.

    Previous = highest (version, revision) below the one released (`derive.release_order`), across
    versions (they run in parallel). `INTERFACE_NOT_BUMPED` reads only that candidate.
    """
    this_order = release_order(release.version, release.revision)
    this_folder = revision_text(release.version, release.revision)
    best: Listing | None = None
    best_order: tuple[int, int] | None = None
    for sibling, sibling_text in listed_siblings(release.path.parent):
        if sibling.name == this_folder:
            continue
        sibling_listing = baseline.loads(sibling_text)
        sibling_order = release_order(sibling_listing.unit.version, sibling_listing.unit.revision)
        if sibling_order >= this_order:
            continue
        if best_order is None or sibling_order > best_order:
            best_order, best = sibling_order, sibling_listing
    return best


def _since_listing(release: _ReleaseTarget) -> Listing | None:
    """The release stored at the model's own revision, else the previous one, or `None`."""
    stored_text = stored_listing(release.path)
    if stored_text is not None:
        return baseline.loads(stored_text)
    return _previous_release_listing(release)


def _changes_since(
    model: Model, releases: Path | None, unit: Id[ModelUnit] | None
) -> ListingDiff | None:
    """The system's `ListingDiff` from the release `_since_listing` finds, or `None`."""
    if releases is None or unit is not None or not projects(model):
        return None
    since = _since_listing(_release_target(model, None, releases))
    return None if since is None else baseline.diff(since, baseline.listing(model, None))


def _pin_source(release: _ReleaseTarget, into: Path) -> tuple[Path, NumberingPins] | None:
    """The pin source: the highest released revision of the same version at or below this one.

    Reads `<into>/<name>/*/baseline/numbering.json` (`listed_siblings`), else `None`; same version
    only, unlike `_previous_release_listing`; a re-release may be its own pin source.
    """
    this_order = release_order(release.version, release.revision)
    best: tuple[Path, NumberingPins] | None = None
    best_order: tuple[int, int] | None = None
    for sibling, listing_text in listed_siblings(into / release.name):
        sibling_listing = baseline.loads(listing_text)
        if not same_version(
            (sibling_listing.unit.name, sibling_listing.unit.version),
            (release.name, release.version),
        ):
            continue
        sibling_order = release_order(sibling_listing.unit.version, sibling_listing.unit.revision)
        if sibling_order > this_order:
            continue
        numbering_text = stored_numbering(sibling)
        if numbering_text is None:
            continue
        if best_order is None or sibling_order > best_order:
            best_order = sibling_order
            best = (sibling, numbering_pins.loads(numbering_text))
    return best


def _interface_not_bumped_findings(
    unit: Id[ModelUnit], release: _ReleaseTarget, new_listing: Listing
) -> list[Finding]:
    """`INTERFACE_NOT_BUMPED`: the previous release, same interface, different boundary.

    Real units only: `_l4_findings` skips the system (interface `""`, boundary empty, so vacuous).
    The previous release is `_previous_release_listing`'s ordered lookup, never a scan of siblings.
    """
    previous = _previous_release_listing(release)
    if previous is None:
        return []
    if previous.unit.interface != new_listing.unit.interface or previous.boundary == (
        new_listing.boundary
    ):
        return []
    previous_revision = revision_text(previous.unit.version, previous.unit.revision)
    return [
        Finding(
            code="INTERFACE_NOT_BUMPED",
            severity=Severity.ERROR,
            subjects=(unit,),
            message=(
                f"{release.name} {previous_revision} already has interface "
                f"{previous.unit.interface!r} with a different boundary"
            ),
        )
    ]


def _release_no_history_finding(
    model: Model, unit: Id[ModelUnit] | None, release: _ReleaseTarget
) -> Finding | None:
    """`RELEASE_NO_HISTORY`: the revision being released has no `Revision` entry."""
    release_id = unit_release(model, unit).id if unit is not None else None
    if current_revision(model, release=release_id) is not None:
        return None
    return Finding(
        code="RELEASE_NO_HISTORY",
        severity=Severity.ERROR,
        subjects=(unit,) if unit is not None else (),
        message=(
            f"{release.name} {revision_text(release.version, release.revision)} has no "
            "Revision history entry"
        ),
    )


def _unit_l4_findings(
    model: Model, unit: Id[ModelUnit], release: _ReleaseTarget, into: Path
) -> list[Finding]:
    """The checks only a real unit has: `INTERFACE_NOT_BUMPED` and the pin findings."""
    new_listing = baseline.listing(model, unit)
    return [
        *_interface_not_bumped_findings(unit, release, new_listing),
        *_revision_pins.pin_findings(model, unit, _pin_source(release, into)),
    ]


def _l4_findings(model: Model, unit: Id[ModelUnit] | None, into: Path) -> tuple[Finding, ...]:
    """The release checks, reading only `<into>` and the model.

    Subject is `unit` or the nested unit; the system has `subjects=()` and skips the unit-only
    checks. Nested checks walk the whole subtree.
    """
    release = _release_target(model, unit, into)
    findings: list[Finding] = []
    already_released = _revision_already_released_finding(model, unit, release)
    if already_released is not None:
        findings.append(already_released)
    findings.extend(_nested_release_findings(model, unit, into))
    if unit is not None:
        findings.extend(_unit_l4_findings(model, unit, release, into))
    no_history = _release_no_history_finding(model, unit, release)
    if no_history is not None:
        findings.append(no_history)
    current = (release.version, release.revision)
    findings.extend(
        history_findings(
            model, unit, name=release.name, current=current, parent=release.path.parent
        )
    )
    return tuple(findings)
