"""The facade's finding codes: build, release and verify (BUILD-MESSAGES M1)."""

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
            "Release the nested unit's new revision, then the containing unit again, or find "
            "why its content changed."
        ),
        page="findings-validators",
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
        fix="Run `fr.rebaseline(result, baselines)`, which re-cuts it under today's rules.",
        page="findings-validators",
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
        fix="Run `fr.rebaseline(result, baselines)`, which records them under today's rules.",
        page="findings-validators",
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
            "verify with the fransys release that cut this baseline, or release a new revision "
            "of the unit, which stores a baseline under today's rules."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="DESIGNATION_MOVED",
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause=(
            "An item or unit instance pinned in the previous release now prints a different "
            "designation, written or numbered."
        ),
        fix="Restore the released tag; only a new version may change it.",
        page="findings-validators",
    ),
    CodeInfo(
        code="DESIGNATION_NEW_IN_REVISION",
        severities=(Severity.INFO,),
        stage="build, release",
        who="note",
        cause="A new untagged item or unit instance took the next free number in a later revision.",
        fix="Nothing is wrong; tag it if its number must stay fixed.",
        page="findings-validators",
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
            "Give the colliding units, items or documents distinct names (or "
            "locations/fragments); two instances of one release name need one document per "
            "release."
        ),
        page="findings-validators",
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
        fix="Bump the interface string if the boundary changed, or restore the previous boundary.",
        page="findings-validators",
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
        fix="Restore the file from version control; a released revision never changes.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RELEASE_FILE_MISSING",
        severities=(Severity.ERROR,),
        stage="verify",
        who="consumer",
        cause="A file its manifest lists, or the manifest itself, is gone from a release folder.",
        fix="Restore it from version control.",
        page="findings-validators",
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
        fix="Remove the entry, or release that revision first. Older entries are free text.",
        page="findings-validators",
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
        fix="Release that nested unit first, then release the containing unit.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RELEASE_NO_HISTORY",
        severities=(Severity.ERROR,),
        stage="release",
        who="consumer",
        cause="The revision being released has no matching `Revision` history entry.",
        fix=(
            "Add the missing entry: `history=` on `@fr.unit`, or `Design.revision(...)` for a "
            "system release."
        ),
        page="findings-validators",
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
        fix="Bump the version or revision, or find why a frozen revision changed.",
        page="findings-validators",
    ),
    CodeInfo(
        code="SYMBOL_PORT_MISSING",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause="A model port matches no port on its drawn symbol by any of the three binding rules.",
        fix="Fix the part's port names, or add a `port_map`/symbol choice.",
        page="findings-render",
    ),
)

BY_CODE: dict[str, CodeInfo] = {
    info.code: info
    for info in (
        *_OWN,
        *vocab.FINDING_CODES,
        *fransys_layout.FINDING_CODES,
        *fransys_render.FINDING_CODES,
        *fransys_pdf.FINDING_CODES,
        *fransys_kicad.FINDING_CODES,
        *fransys_parts.FINDING_CODES,
    )
}
