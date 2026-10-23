"""The facade's finding codes: build, release and verify (BUILD-MESSAGES M1)."""

import fransys_el
import fransys_kicad
import fransys_parts
import fransys_pdf
import fransys_render

import fransys_layout
from fransys_model import vocab
from fransys_model.kernel import CodeInfo, Severity

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BASELINE_DIFFERS",
        severities=(Severity.ERROR,),
        stage="release, verify",
        who="consumer",
        cause=(
            "A unit instance in the released subtree, or checked by `verify`, has a listing "
            "differing from its released baseline."
        ),
        fix=(
            "Bump the changed unit's revision and release it again, or restore its content. "
            "Write: fr.release(result, into, unit=<unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_RULES_MOVED",
        severities=(Severity.INFO, Severity.ERROR),
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline's content is unchanged, but a later fransys prints its listing "
            "differently. `verify` notes it (INFO); `release` of a unit nesting it refuses (ERROR)."
        ),
        fix=(
            "Re-cut the stored baseline under today's rules first. "
            "Write: fr.rebaseline(result, baselines, unit=<unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_ROWS_UNCHECKED",
        severities=(Severity.INFO, Severity.ERROR),
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline cut before fransys 0.18.2 holds rows for a contact block that "
            "today's numbering cannot print. Every other row is unchanged, and those rows were "
            "left out of the comparison. `verify` notes it (INFO); `release` of a unit nesting "
            "it refuses (ERROR)."
        ),
        fix=(
            "Re-cut the stored baseline, which records its rows under today's rules. "
            "Write: fr.rebaseline(result, baselines, unit=<unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="BASELINE_TOO_OLD",
        severities=(Severity.ERROR,),
        stage="release, verify",
        who="consumer",
        cause=(
            "A stored baseline was cut by a fransys older than the oldest release whose listing "
            "rules this build knows, or its manifest records no fransys version."
        ),
        fix=(
            "Verify with the fransys release that cut the baseline, or release a new revision. "
            "Write: fr.release(result, into, unit=<unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="CHANGES_BY_NAME",
        severities=(Severity.INFO,),
        stage="build",
        who="note",
        cause=(
            "The release the next change list starts from was cut before listing version 2, so "
            "it names no item key. The change list matches by printed designation, and a "
            "renamed item shows as one removed and one added row."
        ),
        fix=(
            "The next release's change list follows renames; `fr.rebaseline` re-cuts the old "
            "release now."
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="EXPORT_NAME_CLASH",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two different subjects (documents, items) would write to the same file name in "
            "`out_dir`."
        ),
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
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause=(
            "The previous released revision of this unit (the highest below this one) has the "
            "same interface string but a different boundary."
        ),
        fix=(
            "Bump the interface version of <subject> if its boundary changed, or restore the "
            "previous boundary. Write: fr.unit(<name>, interface_version=<new>, ...)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_FILE_CHANGED",
        severities=(Severity.ERROR,),
        stage="verify",
        who="consumer",
        cause=(
            "A released file's hash differs, the folder holds a file its manifest omits, or "
            "the manifest does not parse. A CRLF-only change in a text file passes."
        ),
        fix=(
            "No call clears this: restore the file from version control; a released revision "
            "never changes."
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_FILE_MISSING",
        severities=(Severity.ERROR,),
        stage="verify",
        who="consumer",
        cause="A file its manifest lists, or the manifest itself, is gone from a release folder.",
        fix="No call clears this: restore it from version control.",
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_HISTORY_UNRELEASED",
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause=(
            "A history entry after the first released one names a revision with no folder "
            "under `into`, in its own version."
        ),
        fix=(
            "Remove the entry from history=, or release that revision first. "
            "Write: fr.release(result, into, unit=<unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_NESTED_UNRELEASED",
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause=(
            "A unit anywhere in the subtree being released (not only direct children) has no "
            "baseline folder yet."
        ),
        fix=(
            "Release <subject> first, then release the containing unit. "
            "Write: fr.release(result, into, unit=<nested unit>)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="RELEASE_NO_HISTORY",
        severities=(Severity.ERROR,),
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
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause=(
            "The unit (or system) being released already has a baseline folder whose listing "
            "differs from the one to be written."
        ),
        fix=(
            "Bump the revision or version, or restore the frozen revision's content. "
            "Write: fr.unit(<name>, revision=<new revision>, ...)"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="SETTING_NEW_ENGINE_ONLY",
        severities=(Severity.WARNING,),
        stage="build",
        who="consumer",
        cause=(
            "A settings file sets a `[grid]` or `[font]` key. It applies to drawings from the new "
            "engine; the old engine, which draws every schematic today, keeps the built-in grid "
            "and font until MODEL-TEXT, so this finding goes then."
        ),
        fix=(
            "Keep the key for the new engine's drawings, or remove it from the settings file. "
            "Write: fr.settings()"
        ),
        page="findings-release",
    ),
    CodeInfo(
        code="SYMBOL_PORT_MISSING",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause="A model port matches no port on its drawn symbol by any of the three binding rules.",
        fix=(
            "Fix the part's port names, or map them with port_map or a symbol choice. Write: "
            "d.layout.symbol(<target>, <symbol>, port_map=<mapping>)"
        ),
        page="findings-render",
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


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return BY_CODE[code].filled(**values)
