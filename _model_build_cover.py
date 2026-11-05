"""A shared `SYSTEM` document for the test builds that have no document of their own.

A test that asserts a layout or render fact needs its build to hold a `Document`, since decision
0037 gates layout on one. This module's `system_document()` gives that build a `SYSTEM`-preset
document (no subject: the only preset with none) with every one of its own default pages removed
(`HARNESS_DRAWING`, `CABLE_LIST`, `BOM` -- `packages/fransys-pdf/src/fransys_pdf/ presets.py`'s
`PRESET_PAGES[DocumentPreset.SYSTEM]`, `COVER`/`NOTES` kept and never empty), leaving nothing for
`fransys_pdf.check` to report as empty (`DOCUMENT_EMPTY_LIST`, `DOCUMENT_NO_TOP_LEVEL_CABLES`)
regardless of what the design does or does not contain.

Verified on the order's own base commit (`model-build-base`, a detached worktree at `3bd82b40`,
where layout still ran unconditionally so both sides of the comparison are real): adding this
exact document to `demo_designs.cabinet_design`, the changeover field case (`in_unit=True`),
`test_units_worked_example._system_design` and `scale_units_fixture.build_scale(2)` changes
`model.digests["layout"]` for NONE of them -- every layout record (`Page`, `SymbolPlacement`,
`LinkMarker`, `Outline`, `DrawingSet`) is identical with and without it -- and adds no
`fr.check` finding beyond the model's own pre-existing ones. So appending this one draft to a
build is mechanical: it re-enables layout with no other observable change.

`cover`'s text is never read for its own content by anything using this module -- `fr.document`
requires a real, existing file (`FileNotFoundError` otherwise), and a `@cache`d test helper
takes no `tmp_path`, so a fixed, tracked file stands in for a per-call temp one.

Importable from every test tree: root `conftest.py` puts the repo root on `sys.path` (for
`demo_designs`), and pytest always loads that conftest for any subset of test paths run against
this repo, so `from _model_build_cover import system_document` works from `tests/`,
`packages/fransys/tests/` and `packages/fransys-layout/tests/` alike.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr
import fransys_parts
from demo_designs import cabinet_design
from fransys_author.design import Design

from fransys_model.kernel import Origin
from fransys_model.vocab import Aspect, AspectNode, DocumentPreset, Unit

if TYPE_CHECKING:
    from fransys import BuildResult

    from fransys_model.kernel import Draft

_COVER = Path(__file__).resolve().parent / "tests" / "_model_build_cover.md"


def system_document() -> Draft:
    """A `SYSTEM` document draft (the preset's own pages; no subject)."""
    return fr.document(DocumentPreset.SYSTEM, None, cover=_COVER)


def layout_trigger_document(subject: object = None) -> Draft:
    """A `CABINET_SCHEMATIC` draft whose SCHEMATIC page makes `fr.build` lay out; `subject` is what it prints.

    With no `subject` it prints the location `LT`, which it adds; a build that must hold no ERROR names its own.
    """
    if subject is not None:
        return fr.document(DocumentPreset.CABINET_SCHEMATIC, subject, cover=_COVER)
    design = Design(fransys_parts.load("demo_parts"))
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, design.location("LT", "Layout trigger"), cover=_COVER)
    draft = design.draft()
    draft.extend(document.records(), origin=Origin(file=__file__, line=1, note="layout trigger"))
    return draft


def printed(draft: Draft) -> tuple[Draft, ...]:
    """`draft` and a `CABINET_SCHEMATIC` document for each of its locations and top-level units: every drawing set of the build prints."""
    subjects = [
        r.id for r in draft.records() if (isinstance(r, AspectNode) and r.aspect is Aspect.LOCATION) or (isinstance(r, Unit) and r.parent is None)
    ]
    return (draft, *(cabinet_document(subject) for subject in subjects)) if subjects else (draft, layout_trigger_document())


def cabinet_document(location: object) -> Draft:
    """A `CABINET_SCHEMATIC` draft for `location`: its page finds drawings."""
    return fr.document(DocumentPreset.CABINET_SCHEMATIC, location, cover=_COVER)


def cabinet_build() -> BuildResult:
    """The demo cabinet design built with its `CABINET_SCHEMATIC` document."""
    parts = fransys_parts.load("demo_parts")
    return fr.build(parts, cabinet_design(parts).draft(), cabinet_document(Design(parts).location("C1", "Demo cabinet")))


def error_codes(result: BuildResult) -> set[str]:
    """The codes of the ERROR findings `fr.check` reports on a build."""
    return {f.code for f in fr.check(result) if f.severity is fr.Severity.ERROR}


def error_messages(result: BuildResult) -> list[str]:
    """The messages of the ERROR findings the build itself carries."""
    return [f.message for f in result.findings if f.severity == fr.Severity.ERROR]


def schematic_document(name: str) -> Draft:
    """A `CABINET_SCHEMATIC` draft for the location `name`, every default page kept."""
    return fr.document(DocumentPreset.CABINET_SCHEMATIC, name, cover=_COVER)


def unit_document(unit: object) -> Draft:
    """A `CABINET_SCHEMATIC` draft for `unit` with its default pages: the unit's drawing set is printed."""
    return fr.document(DocumentPreset.CABINET_SCHEMATIC, unit, cover=_COVER)
