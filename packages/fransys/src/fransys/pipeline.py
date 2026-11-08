"""Pipeline: merge drafts, freeze, run passes, findings policy, the render-once memo."""

import dataclasses
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Mapping

import fransys_pdf
import fransys_render
from fransys_el import block_wire_findings
from fransys_kicad import check as kicad_check
from fransys_parts import library_root
from fransys_parts import lint as parts_lint
from fransys_parts import load as parts_load

from fransys_layout import CableLayout, DiagramLayout, lay_out_cables, lay_out_overview
from fransys_model.derive import (
    ALL_VALIDATORS,
    allocate_plc,
    check_order_hint_cycle,
    check_order_hint_draws_nothing,
    check_unprinted_sets,
    document_sheets_of,
    has_documents,
    number,
    refuses,
    release_identity,
    resolve_wire_rows,
    seed_pins,
    unit_ids,
    unit_release,
)
from fransys_model.derive.numbering_pins import NumberingPins, name_findings
from fransys_model.derive.order import finding_order_key, findings_in_order
from fransys_model.kernel import (
    Finding,
    Id,
    Severity,
    digest_cached,
    evolve,
    freeze,
    merge,
)
lazy import electrical_symbols
lazy from fransys_layout.drawing import Drawing
lazy from fransys_model.kernel import Draft, Model, Origin
lazy from fransys_model.layout import Page
lazy from fransys_model.vocab import Unit as ModelUnit

from . import _args, _revision_pins, _subjects
from ._drawing_library import refuse_authored_library, with_drawing_library
from ._finding_text import described, fix_lines, headed
from ._house import refuse_authored_house, with_house
from ._layout_need import diagram_sheets_of, lay_out_if_needed, needs_schematic_layout
from ._paper import unsupported_sheet_findings
from ._release_checks import (
    _pin_source,
    _ReleaseTarget,
)
from ._seed_facets import assigned_facets, reserved_facets, tag_facets
from ._settings_findings import new_engine_only_findings
from ._settings_library import library_of
from ._times import BuildTimes, Timer
from .errors import FransysError
from .settings import Settings
from .settings import settings as fr_settings

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.derive import SheetBackground, SheetKey
    from fransys_model.vocab import UnitRelease


_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BuildResult:
    """A frozen, laid-out model, every finding collected while building it and its `Settings`."""

    model: Model
    findings: tuple[Finding, ...]
    settings: Settings = dataclasses.field(default_factory=fr_settings)
    times: BuildTimes = dataclasses.field(default=BuildTimes(), compare=False, repr=False)
    drawings: Mapping[Id[Page], Drawing] = dataclasses.field(default=MappingProxyType({}), compare=False, repr=False)
    page_svgs: Mapping[str, str] = dataclasses.field(default=MappingProxyType({}), compare=False, repr=False)
    library: electrical_symbols.Library | None = dataclasses.field(default=None, compare=False, repr=False)
    diagrams: DiagramLayout = dataclasses.field(default=DiagramLayout(diagrams=()), compare=False, repr=False)


class BuildFailedError(FransysError):
    """Raised by `write` or `release` when their own findings hold an `ERROR`.

    No escape hatch: there is no `allow_errors`, `force` or `draft` parameter anywhere in
    this package, and none will be added. `findings` holds every `ERROR` of the run that
    raised, each with its own `fix` template: tests read `exc.findings`, not the message. The
    message is each finding, then its printed fix (`<subject>` and `<other>` filled) and its
    code's findings-row URL.
    `write`'s own findings are resolved through `describe` first (`check`'s own contract);
    `release`'s interface-bump findings are never `describe`d -- their `message` is already
    self-contained, naming the unit, revision and differing sections in plain text.
    """

    def __init__(self, findings: tuple[Finding, ...], *, model: Model) -> None:
        """Store every `ERROR` finding of the run that raised, in `check`'s order."""
        self.findings = findings
        text = ("\n".join([headed(f), *fix_lines(f, model)]) for f in findings)
        super().__init__("\n".join(text))


def parts(*packages: str) -> Draft:
    """Detail: load part libraries by import name and merge them into one `Draft`.

    For a draft that holds only parts, to merge beside other drafts. Try `fr.design(...)` first:
    it loads its libraries itself.

    Each name is an installed part-data package, loaded through `fransys_parts.load`. Zero
    names give an empty Draft. Pass the result to `build` beside other drafts.

    Does not build, lint or freeze; does not accept a folder path (use an import name).
    """
    return merge(*(parts_load(package) for package in packages))


def lint(*libraries: str) -> tuple[Finding, ...]:
    """Read: lint part libraries by import name and return their findings.

    Each root resolves as in `parts`; findings come library by library, in the order given, with
    the part file and line already in the message. Zero libraries give `()`.

    Does not build a model, load a library into a Draft or raise on findings.
    """
    findings: list[Finding] = []
    for library in libraries:
        with library_root(library) as root:
            findings.extend(parts_lint(root))
    return tuple(findings)


def _unit_sources(model: Model, releases: Path) -> dict[Id[ModelUnit], NumberingPins]:
    """Each unit instance's pin source (`_pin_source`), for those that have one."""
    found: dict[Id[ModelUnit], NumberingPins] = {}
    for unit in unit_ids(model):
        target = _ReleaseTarget(identity=release_identity(model, unit), path=Path())
        if (source := _pin_source(target, releases)) is not None:
            found[unit] = source[1]
    return found


def _seed_designation_pins(model: Model, sources: dict[Id[ModelUnit], NumberingPins]) -> Model:
    """Seed assigned and reserved designation facets from pin sources, before numbering.

    Retired, gone or moved pins become reserved facets once per release (instances share a source).
    `build` passes no sources without `releases=`.
    """
    new_facets: list[Any] = []
    origins: dict[Id[Any], Origin] = {}
    seeded_releases: set[Id[UnitRelease]] = set()
    for unit, source_pins in sources.items():
        seeded = seed_pins(model, unit, source_pins)
        new_facets.extend(assigned_facets(model, seeded.assigned, origins))
        new_facets.extend(tag_facets(model, seeded.tags, origins))
        release_record = unit_release(model, unit)
        if release_record.id not in seeded_releases:
            seeded_releases.add(release_record.id)
            new_facets.extend(reserved_facets(model, release_record, seeded.reserved, origins))
    if not new_facets:
        return model
    evolved = evolve(model, put=new_facets, origin=origins[new_facets[0].id])
    merged_origins = frozendict({**evolved.origins, **origins})
    return dataclasses.replace(evolved, origins=merged_origins)


def build(*drafts: Draft | _args.Design, releases: Path | None = None, settings: Settings | None = None) -> BuildResult:
    """Output: merge, freeze and lay out drafts or a `Design` into a `BuildResult`.

    Runs PLC allocation, numbering, every validator and layout, collecting each pass's findings.
    The schematic lays out only when no `ERROR` was found and a `Document` keeps a SCHEMATIC
    page; a symbol with no port for a model port becomes one `SYMBOL_PORT_MISSING` `ERROR`. `releases` seeds
    numbering pins from that release root; `None` numbers freely. `settings` is `fr.settings(...)`;
    `None` takes our defaults. Raises `FreezeError` on a structural problem in the merged draft.

    Does not write files, run `check` or raise on findings; does not seed pins when `releases`
    is `None`.
    """
    timer = Timer()
    chosen = fr_settings() if settings is None else settings
    library = library_of(chosen)
    model = timer.run("merge and freeze", _frozen, drafts, chosen, library)
    model, row_findings = timer.run("wire rows", resolve_wire_rows, model)
    model, plc_findings = timer.run("PLC allocation", allocate_plc, model)
    model, number_findings = timer.run("numbering", _numbered, model, releases)
    found = timer.run(
        "validators",
        _validated,
        model,
        (*new_engine_only_findings(chosen), *unsupported_sheet_findings(model, chosen), *row_findings, *plc_findings, *number_findings),
    )
    if refuses(found) or not has_documents(model):
        return BuildResult(
            model=model,
            findings=_by_code_in_reader_order(found, model),
            settings=chosen,
            times=timer.times(),
            library=library,
        )
    (model, layout_findings, drawn, svgs), diagrams = timer.run("schematic layout", lay_out_if_needed, model, library, chosen.layout)
    found = (*found, *layout_findings, *check_unprinted_sets(model))
    return BuildResult(
        model=model,
        findings=_by_code_in_reader_order(found, model),
        settings=chosen,
        times=timer.times(),
        drawings=MappingProxyType(dict(drawn)),
        page_svgs=MappingProxyType(dict(svgs)),
        library=library,
        diagrams=diagrams,
    )


def _frozen(drafts: tuple[Draft | _args.Design, ...], settings: Settings, library: Library) -> Model:
    """The drafts merged and frozen, with the build's drawing library and paper records."""
    merged = merge(*_args.drafts_of(drafts))
    refuse_authored_library(merged)
    refuse_authored_house(merged)
    return with_drawing_library(with_house(freeze(merged), settings), library)


def _numbered(model: Model, releases: Path | None) -> tuple[Model, tuple[Finding, ...]]:
    """`model` numbered with pins seeded from `releases`, and the numbering findings."""
    sources = {} if releases is None else _unit_sources(model, releases)
    model, findings = number(_seed_designation_pins(model, sources))
    return model, (
        *findings,
        *_revision_pins.new_findings(model, sources),
    )


def _validated(model: Model, earlier: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """`earlier` and every validator's findings, each named."""
    found = [finding for validator in ALL_VALIDATORS for finding in validator(model)]
    found.extend(check_order_hint_cycle(model))
    found.extend(check_order_hint_draws_nothing(model))
    return name_findings(model, (*earlier, *found))


def _by_code_in_reader_order(findings: tuple[Finding, ...], model: Model) -> tuple[Finding, ...]:
    """Each code keeps its first place; its findings list by `finding_order_key` (decision 0135)."""
    by_code: dict[str, list[Finding]] = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)
    return tuple(finding for group in by_code.values() for finding in findings_in_order(model, group))


def _resolved(findings: tuple[Finding, ...], model: Model) -> tuple[Finding, ...]:
    resolved = tuple(dataclasses.replace(finding, message=described(finding, model)) for finding in findings)
    return tuple(
        sorted(
            resolved,
            key=lambda f: (
                _SEVERITY_RANK[f.severity],
                f.code,
                finding_order_key(model, f),
                f.message,
                f.subjects,
            ),
        )
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _Drawn:
    """A model with the page `drawings` its build kept: what `digest_cached` keys by the digest.

    The key names the drawings too: one model drawn with other drawings is another result. The
    cache entry keeps `drawings` alive, so its `id` is not reused while the entry stands.
    """

    model: Model
    drawings: Mapping[Id[Page], Drawing]
    diagrams: DiagramLayout
    library: Library
    page_svgs: Mapping[str, str]

    @property
    def digest(self) -> str:
        return f"{self.model.digest}/{id(self.drawings)}/{id(self.diagrams)}"


@dataclasses.dataclass(frozen=True, slots=True)
class _Read:
    """A model with the library its engine reads: `digest_cached` keys by the digest and the library's identity."""

    model: Model
    library: Library

    @property
    def digest(self) -> str:
        return f"{self.model.digest}/{id(self.library)}"


def _lay_cables(read: _Read) -> CableLayout:
    return lay_out_cables(read.model, read.library)


def _lay_overview(read: _Read) -> tuple[Model, tuple[Finding, ...]]:
    return lay_out_overview(read.model, read.library)


def _draw_svgs(drawn: _Drawn) -> dict[str, str]:
    """Page key to SVG text of the build's core pages, cable blocks and sheets.

    A cable block is keyed by `cable_block_key`, a schematic page by its page id.
    Built once per write/check, reused by `_check`, `_write_intermediates`, `_exports`.
    """
    model = drawn.model
    return {
        **drawn.page_svgs,
        **fransys_render.cable_blocks(model, _cables(_Read(model, drawn.library)), drawn.library),
        **fransys_render.diagram_sheets(model, drawn.library, drawn.diagrams),
    }


# The last model's drawing only (decision 0054): memory stays flat on a big system, and every
# caller of `_svgs` below (`_check`, `write`, `release`) redraws only when the digest changes,
# not on every call. `kernel.digest_cached`, the one per-digest cache every derived result of a
# `Model` uses (model-0067) -- no second cache is written here. `maxsize=1` picks the memo apart
# from `digest_cached`'s other callers (`physical_nets` and friends), which keep
# `DIGEST_CACHE_SIZE` results: those are read many times per build across many models in one
# process (a test suite's many fixtures); `_svgs` is read at most three times (`check`, `write`,
# `release`) for the one model a caller is working on right now, so the last result is enough,
# and it is the cheapest bound this repo's biggest systems allow (WHERE's research file).
_svgs_cache = digest_cached(1)(_draw_svgs)


# The overview engine's one pure call, shared by `check` (its findings) and `write` (the page's
# model), as `_svgs` is (OVERVIEW O25). `build` never runs it: no document, no layout.
_overview = digest_cached(1)(_lay_overview)


# The cable engine's one pure call, shared by `_draw_svgs` and `check` (its block sizes), as
# `_overview` is (layout-0408).
_cables = digest_cached(1)(_lay_cables)


def _draw_sheets(drawn: _Drawn) -> frozendict[SheetKey, SheetBackground]:
    """`fransys_render.sheets` of the model's `document_sheets_of`, in the build's library."""
    return fransys_render.sheets(document_sheets_of(drawn.model, diagram_sheets_of(drawn.diagrams)), drawn.library)


_sheets = digest_cached(1)(_draw_sheets)


def _svgs(drawn: _Drawn) -> dict[str, str]:
    """`_draw_svgs(model)` memoised on `model.digest`, last model only (decision 0054); fresh dict.

    `check`, `write` and `release` are its only callers and treat the dict as read-only;
    the copy keeps that safe by contract.
    """
    return dict(_svgs_cache(drawn))


def _cable_sizes(model: Model, library: Library) -> dict[str, tuple[int, int]]:
    """Each laid-out cable block's `(width, height)` in G, for the pdf check."""
    return {key: (b.width, b.height) for key, b in _cables(_Read(model, library)).blocks.items()}


def _library(result: BuildResult) -> Library:
    """The library the build made; a hand-made `BuildResult` has none and gets its settings'."""
    return result.library or library_of(result.settings)


def _laid_out(result: BuildResult) -> bool:
    """True when the build laid out: no `ERROR`, or a layout `ERROR` in some set while other sets drew (KI-779, R1978)."""
    return not refuses(result.findings) or bool(result.drawings)


def _result_svgs(result: BuildResult) -> dict[str, str]:
    """The drawing of a laid-out `result` (a `Document`, and the sets that laid out); `{}` otherwise."""
    laid_out = _laid_out(result) and has_documents(result.model)
    drawn = _Drawn(result.model, result.drawings, result.diagrams, _library(result), result.page_svgs)
    return _svgs(drawn) if laid_out else {}


def _raw_findings(result: BuildResult, svgs: dict[str, str]) -> tuple[Finding, ...]:
    """Every finding of a build before `describe`.

    `describe` embeds `file:line (key)`, not reproducible across checkouts, so `release`'s manifest
    reads each WARNING's raw `message` from here.
    """
    model = result.model
    raw = list(result.findings)
    for board in _subjects.boards(model):
        raw.extend(kicad_check(model, board))
    if _laid_out(result):
        raw.extend(_overview(_Read(model, _library(result)))[1])
    if _laid_out(result) and has_documents(model):
        sheets = diagram_sheets_of(result.diagrams)
        raw.extend(
            fransys_pdf.check(
                model, svgs, diagrams=sheets, laid=_cable_sizes(model, _library(result)), pdf=cast("Mapping[str, float]", result.settings.pdf)
            )
        )
        raw.extend(fransys_render.sheet_check(model, document_sheets_of(model, sheets)))
        raw.extend(block_wire_findings(model, _cables(_Read(model, _library(result)))))
        if needs_schematic_layout(model):
            raw.extend(fransys_render.check(model))
    return tuple(raw)


def _check(result: BuildResult, svgs: dict[str, str]) -> tuple[Finding, ...]:
    return _resolved(_raw_findings(result, svgs), result.model)


def check(result: BuildResult) -> tuple[Finding, ...]:
    """Output: collect every finding about a built model.

    They are `build`'s, plus the KiCad, PDF and render checks.

    Findings come back ordered `ERROR`, `WARNING`, `INFO`, then by `(code, subjects, message)`,
    each message already run through `describe` so subjects read `file:line (key)`. The PDF and
    render checks run only on a laid-out model (no `ERROR`, at least one `Document`); the KiCad
    check always runs.

    Does not raise on findings, write files or draw a page for a model that was never laid out.
    """
    return _check(result, _result_svgs(result))
