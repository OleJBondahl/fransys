"""A shared `SYSTEM` document for MODEL-BUILD PS4's no-document test builds.

`.fransys/WORK-ORDER-MODEL-BUILD.md`, Part 3: a test that asserts a layout or render fact
needs its build to hold a `Document`, since decision 0037 (PS1/PS2) gates layout on one. This
module's `system_document()` gives that build a `SYSTEM`-preset document (no subject, units
spec: the only preset with none) with every one of its own default pages removed
(`HARNESS_DRAWING`, `CABLE_LIST`, `BOM` -- `packages/fransys-pdf/src/fransys_pdf/
presets.py`'s `PRESET_PAGES[DocumentPreset.SYSTEM]`, `COVER`/`NOTES` kept and never empty),
leaving nothing for `fransys_pdf.check` to report as empty (`DOCUMENT_EMPTY_LIST`,
`DOCUMENT_NO_TOP_LEVEL_CABLES`) regardless of what the design does or does not contain.

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

from fransys_model.vocab import DocumentPreset, PageKind

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

_COVER = Path(__file__).resolve().parent / "tests" / "_model_build_cover.md"
_EMPTY_ON_A_BLANK_MODEL = (PageKind.HARNESS_DRAWING, PageKind.CABLE_LIST, PageKind.BOM)
_KEEPS_LAYOUT = (PageKind.SCHEMATIC,)


def system_document() -> Draft:
    """A `SYSTEM` document draft with no page that could report itself empty."""
    return fr.document(DocumentPreset.SYSTEM, None, cover=_COVER, remove=_EMPTY_ON_A_BLANK_MODEL)


def layout_trigger_document() -> Draft:
    """SYSTEM plus SCHEMATIC so fr.build lays out; it never checks or writes clean (DOCUMENT_NO_DRAWINGS)."""  # noqa: E501 -- the ruled one-line docstring
    return fr.document(
        DocumentPreset.SYSTEM,
        None,
        cover=_COVER,
        add=_KEEPS_LAYOUT,
        remove=_EMPTY_ON_A_BLANK_MODEL,
    )


def cabinet_document(location: object) -> Draft:
    """A `CABINET_SCHEMATIC` draft for `location`, SCHEMATIC kept: its page finds drawings."""
    return fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        location,
        cover=_COVER,
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
    )
