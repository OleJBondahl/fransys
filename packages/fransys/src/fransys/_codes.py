"""The facade's finding codes: build, release and verify (BUILD-MESSAGES M1)."""

from typing import Any
lazy from collections.abc import Iterable

import fransys_el
import fransys_kicad
import fransys_parts
import fransys_pdf
import fransys_render

import fransys_layout
from fransys_model import vocab
from fransys_model.kernel import CodeInfo, Finding, Id, Severity

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BASELINE_DIFFERS",
        severity=Severity.ERROR,
        stage="release, verify",
        who="consumer",
        cause=("A unit instance in the released subtree, or checked by `verify`, has a listing differing from its released baseline."),
        fix=("Bump the changed unit's revision and release it again, or restore its content. Write: fr.release(result, into, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_RULES_MOVED_NOTE",
        severity=Severity.INFO,
        stage="release, verify",
        who="consumer",
        cause=("A stored baseline's content is unchanged, but a later fransys prints its listing differently; `verify` notes it."),
        fix=("Re-cut the stored baseline under today's rules first. Write: fr.rebaseline(result, baselines, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_RULES_MOVED_REFUSED",
        severity=Severity.ERROR,
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline's content is unchanged, but a later fransys prints its listing differently; `release` of a unit nesting it refuses."
        ),
        fix=("Re-cut the stored baseline under today's rules first. Write: fr.rebaseline(result, baselines, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_ROWS_UNCHECKED_NOTE",
        severity=Severity.INFO,
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline cut before fransys 0.18.2 holds rows for a contact block "
            "that today's numbering cannot print; those rows were left out of the "
            "comparison and `verify` notes it."
        ),
        fix=("Re-cut the stored baseline, which records its rows under today's rules. Write: fr.rebaseline(result, baselines, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_ROWS_UNCHECKED_REFUSED",
        severity=Severity.ERROR,
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline cut before fransys 0.18.2 holds rows for a contact block "
            "that today's numbering cannot print; those rows were left out of the "
            "comparison and `release` of a unit nesting it refuses."
        ),
        fix=("Re-cut the stored baseline, which records its rows under today's rules. Write: fr.rebaseline(result, baselines, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_TOO_OLD",
        severity=Severity.ERROR,
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline was cut by a fransys older than the oldest release whose listing "
            "rules this build knows, or its manifest records no fransys version."
        ),
        fix=("Verify with the fransys release that cut the baseline, or release a new revision. Write: fr.release(result, into, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="EXPORT_NAME_CLASH",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=("Two different subjects (documents, items) would write to the same file name in `out_dir`."),
        fix=(
            "Give <subject> or <other> a distinct name, location or fragment; a placement of a "
            "release is named by what `d.add` returned, which adds its tag to the PDF name. "
            "Write: fr.unit(<distinct name>, revision=<n>, interface_version=<n>, "
            "date=<date>, text=<text>, by=<by>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="INTERFACE_NOT_BUMPED",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause=("The previous released revision of this unit (the highest below this one) has the same interface string but a different boundary."),
        fix=(
            "Bump the interface version of <subject> if its boundary changed, or restore the "
            "previous boundary. Write: fr.unit(<name>, interface_version=<new>, ...)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_FILE_CHANGED",
        severity=Severity.ERROR,
        stage="verify",
        who="consumer",
        cause=(
            "A released file's hash differs, the folder holds a file its manifest omits, or "
            "the manifest does not parse. A CRLF-only change in a text file passes."
        ),
        fix=("No call clears this: restore the file from version control; a released revision never changes."),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_FILE_MISSING",
        severity=Severity.ERROR,
        stage="verify",
        who="consumer",
        cause=("A file its manifest lists, or the manifest itself, is gone from a release folder."),
        fix="No call clears this: restore it from version control.",
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_HISTORY_UNRELEASED",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause=("A history entry after the first released one names a revision with no folder under `into`, in its own version."),
        fix=("Remove the entry from history=, or release that revision first. Write: fr.release(result, into, unit=<unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_NESTED_UNRELEASED",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause=("A unit anywhere in the subtree being released (not only direct children) has no baseline folder yet."),
        fix=("Release <subject> first, then release the containing unit. Write: fr.release(result, into, unit=<nested unit>)"),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_NO_HISTORY",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause="The revision being released has no matching `Revision` history entry.",
        fix=(
            "Add the missing entry: history= on fr.unit, or d.revision(...) for a system "
            "release. Write: fr.unit(<name>, ..., history=[<revision entry>])"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="REVISION_ALREADY_RELEASED",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause=("The unit (or system) being released already has a baseline folder whose listing differs from the one to be written."),
        fix=("Bump the revision or version, or restore the frozen revision's content. Write: fr.unit(<name>, revision=<new revision>, ...)"),
        page="findings-release",
    ),
    CodeInfo(
        code="SETTING_NEW_ENGINE_ONLY",
        severity=Severity.WARNING,
        stage="build",
        who="consumer",
        cause=(
            "A settings file sets a `[font]` key. It applies to drawings from the new "
            "engine; the old engine, which draws every schematic today, keeps the built-in font "
            "until MODEL-TEXT, so this finding goes then."
        ),
        fix=("Keep the key for the new engine's drawings, or remove it from the settings file. Write: fr.settings()"),
        page="findings-release",
    ),
    CodeInfo(
        code="SHEET_FORMAT_NOT_SUPPORTED",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=(
            "A sheet record, or a unit's layout profile, uses a paper that is not A3 or A2 landscape. "
            "The supported formats are closed: a portrait sheet (height above width) and a sheet of any other size are refused."
        ),
        fix=("Use a sheet of A3 or A2 landscape: take the default A3, or name A3 or A2 in the settings. Write: fr.settings(paper=...)"),
        page="findings-release",
    ),
)

BY_CODE: dict[str, CodeInfo] = {
    info.code: info
    for info in (
        *_OWN,
        *vocab.FINDING_CODES,
        *fransys_el.FINDING_CODES,
        *fransys_layout.FINDING_CODES,
        *fransys_render.FINDING_CODES,
        *fransys_pdf.FINDING_CODES,
        *fransys_kicad.FINDING_CODES,
        *fransys_parts.FINDING_CODES,
    )
}


def finding(code: str, subjects: Iterable[Id[Any]], message: str, **fix_values: str) -> Finding:
    """The `Finding` of `code`: its one severity, its fix filled from `fix_values`."""
    return BY_CODE[code].finding(subjects, message, **fix_values)
