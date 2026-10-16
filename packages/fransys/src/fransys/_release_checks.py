"""The release identity and the checks `release`, `diff`, `verify` and `write` share.

`_release_target` computes `<into>/<name>/<version>.<revision>/` once; the L4 checks read it.
"""

import dataclasses
from typing import TYPE_CHECKING
lazy from pathlib import Path

from fransys_model.derive import (
    baseline,
    current_revision,
    has_project,
    listing_interface,
    listing_revision_text,
    nested_units,
    pin_source_pins,
    previous_release_listing,
    release_identity,
    revision_text,
    unit_release,
)
from fransys_model.kernel import Finding, Id, Severity
lazy from fransys_model.derive.numbering_pins import NumberingPins

from . import _revision_pins
from ._baseline_findings import baseline_findings
from ._history_gate import history_findings
from ._release_files import folder_findings
from ._release_reader import manifest_readable, read_stored, stored_listing

if TYPE_CHECKING:
    from fransys_model.derive.baseline import Listing, ListingDiff, ReleaseIdentity
    from fransys_model.kernel import Model
    from fransys_model.vocab import Unit as ModelUnit


@dataclasses.dataclass(frozen=True, slots=True)
class _ReleaseTarget:
    """A unit's, or the system's, release identity and target directory.

    Bundles `_release_target`'s result so `release` and every `_l4_findings` check pass one value.
    """

    identity: ReleaseIdentity
    path: Path

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def version(self) -> int:
        return self.identity.version

    @property
    def revision(self) -> int:
        return self.identity.revision


def _release_target(model: Model, unit: Id[ModelUnit] | None, into: Path) -> _ReleaseTarget:
    """A unit's, or the system's, release name, version, revision and target directory.

    The one place `<into>/<name>/<version>.<revision>/` is computed; `release`, `_l4_findings` call.
    """
    identity = release_identity(model, unit)
    path = into / identity.name / revision_text(identity.version, identity.revision)
    return _ReleaseTarget(identity=identity, path=path)


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


def _nested_release_findings(model: Model, unit: Id[ModelUnit] | None, into: Path) -> list[Finding]:
    """`RELEASE_NESTED_UNRELEASED` and the `baseline_findings`: the whole subtree, any depth."""
    findings: list[Finding] = []
    for nested in nested_units(model, unit):
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
        if not manifest_readable(nested_release.path):
            findings.extend(folder_findings(nested_release.path))
            continue
        findings.extend(
            baseline_findings(model, nested, nested_release, nested_stored_text, nested=True)
        )
    return findings


def _previous_release_listing(release: _ReleaseTarget) -> Listing | None:
    """The stored listing of the previous release (`derive.previous_release_listing`), or `None`.

    `INTERFACE_NOT_BUMPED` and `changes.md` read only that candidate.
    """
    stored = read_stored(release.path.parent)
    return previous_release_listing(stored, release.identity)


def _since_listing(release: _ReleaseTarget) -> Listing | None:
    """The release stored at the model's own revision, else the previous one, or `None`."""
    stored_text = stored_listing(release.path)
    if stored_text is not None:
        return baseline.loads(stored_text)
    return _previous_release_listing(release)


def _system_since(model: Model, releases: Path | None) -> Listing | None:
    """The system's listing `_since_listing` finds, or `None` (no folder or no project)."""
    if releases is None or not has_project(model):
        return None
    return _since_listing(_release_target(model, None, releases))


def _changes_since(
    model: Model, releases: Path | None, unit: Id[ModelUnit] | None
) -> ListingDiff | None:
    """The system's `ListingDiff` from the release `_system_since` finds, or `None`."""
    since = None if unit is not None else _system_since(model, releases)
    return None if since is None else baseline.diff(since, baseline.listing(model, None))


def changes_by_name_findings(model: Model, releases: Path | None) -> list[Finding]:
    """`CHANGES_BY_NAME`: the release the next change list starts from has no item keys (CR3).

    The system only, as `_changes_since`; the diff then matches by printed text, so a rename shows
    as a removed and an added row. A release cut at listing version 2 or later gives none.
    """
    since = _system_since(model, releases)
    label = None if since is None else baseline.keyless_release(since)
    if label is None:
        return []
    return [
        Finding(
            code="CHANGES_BY_NAME",
            severity=Severity.INFO,
            subjects=(),
            message=(
                f"renames are not followed: the listing of {label} has no "
                "item keys; fr.rebaseline re-cuts it with them"
            ),
        )
    ]


def _pin_source(release: _ReleaseTarget, into: Path) -> tuple[Path, NumberingPins] | None:
    """The pin source (`derive.pin_source_pins`) as its folder and numbering, or `None`."""
    source = pin_source_pins(read_stored(into / release.name), release.identity)
    return None if source is None else (into / release.name / source[0], source[1])


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
    if listing_interface(previous) != listing_interface(new_listing) or not (
        baseline.boundary_changed(previous, new_listing)
    ):
        return []
    previous_revision = listing_revision_text(previous)
    return [
        Finding(
            code="INTERFACE_NOT_BUMPED",
            severity=Severity.ERROR,
            subjects=(unit,),
            message=(
                f"{release.name} {previous_revision} already has interface "
                f"{listing_interface(previous)!r} with a different boundary"
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
