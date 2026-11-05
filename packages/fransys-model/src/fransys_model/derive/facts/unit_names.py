"""Matching a unit instance by its release's name (spec unit-subject-by-name).

Its one home: `derive.document_unit` and the `DOCUMENT_UNIT_UNRESOLVED` check import the match
from here.
"""

lazy from collections.abc import Mapping

from fransys_model.derive.facts.children import unit_parent
from fransys_model.kernel import Id, Model, ModelError
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.revision_text import revision_text
from fransys_model.vocab.tables import unit_releases, units
lazy from fransys_model.vocab.core import Unit, UnitRelease

_ADVICE = "build the unit alone, or pass the instance's scope"


def units_named(model: Model, name: str) -> tuple[Id[Unit], ...]:
    """The ids of every `Unit` instance of a release named `name`, in id order.

    Every version and revision of that name counts; an id order that does not depend on
    hash order (the tie-break).

    Example: two `UnitRelease`s named `"relay-board"` (`1.1` and `1.2`), one `Unit`
    instance of each: `units_named(model, "relay-board")` returns both ids, sorted.
    """
    named_releases = {release.id for release in unit_releases(model).values() if release.name == name}
    return tuple(unit_id for unit_id, unit in units(model).items() if unit.release in named_releases)


def unit_name_unresolved(model: Model, name: str) -> str:
    """The one sentence for a `unit_name` that does not resolve to exactly one unit.

    Called only when `units_named(model, name)` is not exactly one match. Three cases, each
    ending with the same advice: no release has `name` (says so and names the release names
    the model does have, or that it has none); releases of `name` exist but no instance is in
    the model (names their versions and revisions); several instances match (names each, with
    its release's version and revision and, if it has a parent, where it sits).

    Example: `unit_name_unresolved(model, "relay-board")` with no such release returns
    `"no unit release is named 'relay-board'; the model has 'io-board'. Build the unit alone,
    or pass the instance's scope."`

    Raises:
        ModelError: `name` has exactly one matching unit; there is nothing to report.
    """
    matches = units_named(model, name)
    if len(matches) == 1:
        msg = f"{name!r} resolves to exactly one unit; there is nothing to report"
        raise ModelError(msg)
    releases = unit_releases(model)
    named_releases = sorted(
        (release for release in releases.values() if release.name == name),
        key=lambda release: (release.version, release.revision),
    )
    if not named_releases:
        return _no_release(releases, name)
    if not matches:
        versions = ", ".join(revision_text(release.version, release.revision) for release in named_releases)
        return f"unit release {name!r} exists ({versions}) but no unit in the model is an instance of it. {_ADVICE.capitalize()}."
    texts = "; ".join(_instance_text(model, unit_id) for unit_id in matches)
    return f"{len(matches)} units are instances of {name!r}: {texts}. {_ADVICE.capitalize()}."


def _no_release(releases: Mapping[Id[UnitRelease], UnitRelease], name: str) -> str:
    """The sentence for a name no release has."""
    available = sorted({release.name for release in releases.values()})
    known = ", ".join(repr(release_name) for release_name in available) if available else "none"
    return f"no unit release is named {name!r}; the model has {known}. {_ADVICE.capitalize()}."


def _instance_text(model: Model, unit_id: Id[Unit]) -> str:
    """One matching instance: its ref, its release's version and revision, and its parent."""
    all_units = units(model)
    unit = all_units[unit_id]
    release = unit_releases(model)[unit.release]
    parent = unit_parent(model, unit_id)
    under = "" if parent is None else f" under {ref(all_units[parent])}"
    return f"{ref(unit)} ({revision_text(release.version, release.revision)}){under}"
