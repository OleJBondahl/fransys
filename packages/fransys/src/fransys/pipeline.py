"""Pipeline: merge drafts, freeze, run passes, findings policy, write files."""

import dataclasses
import glob
import shutil
import tempfile
from functools import cache, partial
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Callable, Mapping

import fransys_pdf
import fransys_render
import typst
from fransys_kicad import check as kicad_check
from fransys_kicad import netlist as kicad_netlist
from fransys_overview import html as overview_html
from fransys_parts import library_root
from fransys_parts import lint as parts_lint
from fransys_parts import load as parts_load
from fransys_reports import (
    bom_csv,
    cables_csv,
    changes_csv,
    changes_markdown,
    cores_csv,
    designations_csv,
    plc_csv,
    wires_csv,
)
from fransys_reports import (
    connectors_csv as connectors_csv_of,
)
from fransys_reports import (
    terminal_csv as terminal_csv_of,
)
from fransys_wago import modules_xml as modules_xml_of

import electrical_symbols
from fransys_layout import lay_out_cables, lay_out_overview
from fransys_model.derive import (
    ALL_VALIDATORS,
    allocate_plc,
    baseline,
    check_pins_below,
    check_side_hints,
    check_unprinted_sets,
    document_sheets_of,
    document_stems,
    errors_of,
    export_set,
    export_set_name,
    gone_or_moved,
    has_documents,
    has_project,
    list_context,
    number,
    numbering_pins,
    reference_fragment,
    refuses,
    release_identity,
    release_names,
    resolve_wire_rows,
    seed_pins,
    stale_patterns,
    unit_ids,
    unit_name_unresolved,
    unit_release,
    units_named,
)
from fransys_model.derive.numbering_pins import NumberingPins, name_findings
from fransys_model.derive.order import finding_order_key, findings_in_order
from fransys_model.derive.page_nav import reference_links
from fransys_model.kernel import (
    Finding,
    Id,
    Severity,
    digest_cached,
    evolve,
    freeze,
    merge,
)
from fransys_model.kernel import dumps as model_dumps
lazy from fransys_layout.drawing import Drawing
lazy from fransys_model.kernel import Draft, Model, Origin
lazy from fransys_model.layout import Page
lazy from fransys_model.vocab import Unit as ModelUnit

from . import _args, _revision_pins, _subjects
from ._baseline_findings import baseline_findings
from ._drawing_library import refuse_authored_library, with_drawing_library
from ._export_ledger import _DATA_DIR, _ExportLedger, _placed
from ._finding_text import described, fix_lines, headed
from ._layout_core import draw_on_core
from ._layout_need import lay_out_if_needed, needs_schematic_layout
from ._paper import refuse_authored_paper, with_paper
from ._rebaseline import plan_rebaseline, write_plan
from ._release_checks import (
    _changes_since,
    _l4_findings,
    _pin_source,
    _previous_release_listing,
    _release_target,
    _ReleaseTarget,
    _since_listing,
    changes_by_name_findings,
)
from ._release_files import release_file_findings
from ._release_manifest import _manifest
from ._release_reader import BASELINE_FILES, stored_listing
from ._seed_facets import assigned_facets, reserved_facets, tag_facets
from ._settings_findings import new_engine_only_findings
from ._settings_library import build_library, font_dirs
from ._times import TIMES_FILE, BuildTimes, Timer
from .documents import engine_subject
from .settings import Settings
from .settings import settings as fr_settings

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.derive import SheetBackground, SheetKey
    from fransys_model.derive.baseline import ListingDiff
    from fransys_model.vocab import UnitRelease

_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


def _put(path: Path, data: bytes) -> None:
    """Write `data` to `path`, making `data/` when it is the first file there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BuildResult:
    """A frozen, laid-out model, every finding collected while building it and its `Settings`."""

    model: Model
    findings: tuple[Finding, ...]
    settings: Settings = dataclasses.field(default_factory=fr_settings)
    times: BuildTimes = dataclasses.field(default=BuildTimes(), compare=False, repr=False)
    drawings: Mapping[Id[Page], Drawing] = dataclasses.field(
        default=MappingProxyType({}), compare=False, repr=False
    )


class BuildErrors(Exception):  # noqa: N818 -- plural on purpose: it carries every error finding
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


def _has_document(model: Model) -> bool:
    return has_documents(model)


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


def build(
    *drafts: Draft | _args.Design, releases: Path | None = None, settings: Settings | None = None
) -> BuildResult:
    """Output: merge, freeze and lay out drafts or a `Design` into a `BuildResult`.

    Runs PLC allocation, numbering, every validator and layout, collecting each pass's findings.
    The schematic lays out only when no `ERROR` was found and a `Document` keeps a SCHEMATIC
    page; a layout `SymbolPortError` becomes one `SYMBOL_PORT_MISSING` `ERROR`. `releases` seeds
    numbering pins from that release root; `None` numbers freely. `settings` is `fr.settings(...)`;
    `None` takes our defaults. Raises `FreezeError` on a structural problem in the merged draft.

    Does not write files, run `check` or raise on findings; does not seed pins when `releases`
    is `None`.
    """
    timer = Timer()
    chosen = fr_settings() if settings is None else settings
    library = build_library(chosen.grid, chosen.font, "the settings")
    model = timer.run("merge and freeze", _frozen, drafts, chosen, library)
    model, row_findings = timer.run("wire rows", resolve_wire_rows, model)
    model, plc_findings = timer.run("PLC allocation", allocate_plc, model)
    model, number_findings = timer.run("numbering", _numbered, model, releases)
    found = timer.run(
        "validators",
        _validated,
        model,
        (*new_engine_only_findings(chosen), *row_findings, *plc_findings, *number_findings),
    )
    if refuses(found) or not _has_document(model):
        return BuildResult(
            model=model,
            findings=_by_code_in_reader_order(found, model),
            settings=chosen,
            times=timer.times(),
        )
    model, layout_findings, drawn, _links = timer.run(
        "schematic layout", lay_out_if_needed, model, library, chosen.layout
    )
    model, cable_findings = timer.run("cable layout", lay_out_cables, model)
    found = (*found, *layout_findings, *cable_findings, *check_unprinted_sets(model))
    return BuildResult(
        model=model,
        findings=_by_code_in_reader_order(found, model),
        settings=chosen,
        times=timer.times(),
        drawings=MappingProxyType(dict(drawn)),
    )


def _frozen(
    drafts: tuple[Draft | _args.Design, ...], settings: Settings, library: Library
) -> Model:
    """The drafts merged and frozen, with the build's drawing library and paper records."""
    merged = merge(*_args.drafts_of(drafts))
    refuse_authored_library(merged)
    refuse_authored_paper(merged)
    return with_paper(with_drawing_library(freeze(merged), library), settings)


def _numbered(model: Model, releases: Path | None) -> tuple[Model, tuple[Finding, ...]]:
    """`model` numbered with pins seeded from `releases`, and the numbering findings."""
    sources = {} if releases is None else _unit_sources(model, releases)
    model, findings = number(_seed_designation_pins(model, sources))
    return model, (
        *findings,
        *_revision_pins.new_findings(model, sources),
        *changes_by_name_findings(model, releases),
    )


def _validated(model: Model, earlier: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """`earlier` and every validator's findings, each named."""
    found = [finding for validator in ALL_VALIDATORS for finding in validator(model)]
    found.extend(check_side_hints(model))
    found.extend(check_pins_below(model))
    return name_findings(model, (*earlier, *found))


def _by_code_in_reader_order(findings: tuple[Finding, ...], model: Model) -> tuple[Finding, ...]:
    """Each code keeps its first place; its findings list by `finding_order_key` (decision 0135)."""
    by_code: dict[str, list[Finding]] = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)
    return tuple(
        finding for group in by_code.values() for finding in findings_in_order(model, group)
    )


def _resolved(findings: tuple[Finding, ...], model: Model) -> tuple[Finding, ...]:
    resolved = tuple(
        dataclasses.replace(finding, message=described(finding, model)) for finding in findings
    )
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

    @property
    def digest(self) -> str:
        return f"{self.model.digest}/{id(self.drawings)}"


def _draw_svgs(drawn: _Drawn) -> dict[str, str]:
    """Page key to SVG text of the core's pages and `fransys_render`'s cable blocks and sheets.

    A cable block is keyed by `cable_block_key`, a schematic page by its page id.
    Built once per write/check, reused by `_check`, `_write_intermediates`, `_exports`.
    """
    model = drawn.model
    pages: dict[str, str] = {}
    if needs_schematic_layout(model):
        pages = draw_on_core(model, drawn.drawings, electrical_symbols.LIBRARY)
    return {**pages, **fransys_render.cable_blocks(model), **fransys_render.diagram_sheets(model)}


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
_overview = digest_cached(1)(lay_out_overview)
# Every page background (frame, grid, title block) of every document, drawn once per model and
# read by each document's `source` (render-0019).


def _draw_sheets(model: Model) -> frozendict[SheetKey, SheetBackground]:
    """`fransys_render.sheets` of the model's `document_sheets_of`."""
    return fransys_render.sheets(document_sheets_of(model))


_sheets = digest_cached(1)(_draw_sheets)
_bridges = cache(fransys_render.bridge_pieces)  # the same two drawings for every model


def _svgs(model: Model, drawings: Mapping[Id[Page], Drawing]) -> dict[str, str]:
    """`_draw_svgs(model)` memoised on `model.digest`, last model only (decision 0054); fresh dict.

    `check`, `write` and `release` are its only callers and treat the dict as read-only;
    the copy keeps that safe by contract.
    """
    return dict(_svgs_cache(_Drawn(model, drawings)))


def _result_svgs(result: BuildResult) -> dict[str, str]:
    """The drawing of a laid-out `result` (no `ERROR`, a `Document`); `{}` otherwise."""
    laid_out = not refuses(result.findings) and _has_document(result.model)
    return _svgs(result.model, result.drawings) if laid_out else {}


def _raw_findings(result: BuildResult, svgs: dict[str, str]) -> tuple[Finding, ...]:
    """Every finding of a build before `describe`.

    `describe` embeds `file:line (key)`, not reproducible across checkouts, so `release`'s manifest
    reads each WARNING's raw `message` from here.
    """
    model = result.model
    raw = list(result.findings)
    for board in _subjects.boards(model):
        raw.extend(kicad_check(model, board))
    if not refuses(result.findings):
        raw.extend(_overview(model)[1])
    if not refuses(result.findings) and _has_document(model):
        raw.extend(fransys_pdf.check(model, svgs, result.findings))
        raw.extend(fransys_render.sheet_check(model, document_sheets_of(model)))
        if needs_schematic_layout(model):
            raw.extend(fransys_render.check(model, result.findings))
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


def _file_safe(page_key: str) -> str:
    """`page_key` as a filesystem-safe name fragment.

    `:` opens an NTFS alternate stream on Windows, so a naive write silently produces no `.svg`.
    """
    return page_key.replace(":", "-")


def _write_intermediates(
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    svgs: dict[str, str],
    intermediates: Path,
    pdf: Mapping[str, object],
) -> None:
    """Page SVGs, netlists and Typst source that never reach `out_dir`; written before the gate.

    A half-finished design still draws; an errored build has no pages (decision 0028, model-0077).
    Typst is not compiled here (fonts: `_exports`); pages come from the built `svgs`.
    """
    for page_key, svg in svgs.items():
        (intermediates / f"{_file_safe(page_key)}.svg").write_bytes(svg.encode("utf-8"))
    for board in _subjects.boards(model):
        text = kicad_netlist(model, board)
        (intermediates / f"netlist-{reference_fragment(model, board)}.net").write_bytes(
            text.encode("utf-8")
        )
    for document_id, stem in document_stems(model):
        source_text = _pdf_source(model, drawings, document_id, svgs, pdf)
        (intermediates / f"{stem}.typ").write_bytes(source_text.encode("utf-8"))


def _pdf_source(
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    document_id: Id[Any],
    svgs: dict[str, str],
    pdf: Mapping[str, object],
) -> str:
    """One document's Typst source, with the list-page shares from the `[pdf]` settings."""
    known = frozenset(drawings)
    return fransys_pdf.source(
        model,
        document_id,
        svgs,
        _sheets(model),
        _bridges(),
        links={page: reference_links(model, page, known) for page in known},
        list_share_pct=cast("float", pdf["list_share_pct"]),
        list_gutter_pct=cast("float", pdf["list_gutter_pct"]),
    )


def _compile_pdf(  # noqa: PLR0913 -- the build's drawings join the model, document, svgs, fonts and pdf settings
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    document_id: Id[Any],
    svgs: dict[str, str],
    fonts: tuple[Path, ...] = (),
    *,
    pdf: Mapping[str, object],
) -> bytes:
    """One document's Typst source, compiled to PDF bytes (decision pdf-0001).

    Touches font files, so only here, never in pure `fransys_pdf`; passes no `timestamp=`:
    the date is the source's `#set document(date: ...)`; Typst reads one only for `auto` (0030).
    """
    source_text = _pdf_source(model, drawings, document_id, svgs, pdf)
    compiler = typst.Compiler(
        font_paths=list(fonts) or [electrical_symbols.font_dir()], ignore_system_fonts=True
    )
    try:
        compiled = compiler.compile(input=source_text.encode("utf-8"))
    except typst.TypstError as error:
        overflow = fransys_pdf.cover_overflow_finding(document_id, str(error))
        if overflow is None:
            raise
        raise BuildErrors(_resolved((overflow,), model), model=model) from error
    # typst.Compiler.compile's stub types every call `bytes | list[bytes] | None` because the
    # union also covers `output=<path>` (writes to disk, returns `None`) and multi-file input
    # (returns `list[bytes]`); this call passes neither, so it always returns `bytes` (confirmed
    # by compiling, decision pdf-0001's addendum).
    assert isinstance(compiled, bytes)  # noqa: S101 -- narrows a stub union that no overload covers for this call shape
    return compiled


def _resolve_unit(model: Model, unit: object) -> Id[ModelUnit] | None:
    """`unit=` (`None` or a release name) as a unit id or `None`.

    `units_named` is the one home of name matching; its message is used verbatim.
    """
    unit = engine_subject(unit)
    if unit is None:
        return None
    if isinstance(unit, str):
        matches = units_named(model, unit)
        if len(matches) == 1:
            return matches[0]
        raise ValueError(unit_name_unresolved(model, unit))
    if isinstance(unit, Id | _args.Scope):
        return _subjects.unit_of(unit, "write()'s unit=", "a unit Id instead")
    msg = f"unit= must be a release name or None, not {type(unit).__name__}"
    raise TypeError(msg)


def _list_context(model: Model, unit: Id[ModelUnit] | None, subject: Id[Any]) -> Id[Any] | None:
    """The list context a CSV prints its ends in (model-0054 section 4); none in `out/all/`."""
    return None if unit is None else list_context(model, subject)


def _produce(make: Callable[[Id[Any]], Callable[[], str | bytes]], subject: Id[Any]) -> str | bytes:
    return make(subject)()


def _producers(  # noqa: PLR0913, PLR0917 -- one parameter per input of the exports, as `_ledger`
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    svgs: dict[str, str],
    unit: Id[ModelUnit] | None,
    findings: tuple[Finding, ...],
    changes: ListingDiff | None,
    fonts: tuple[Path, ...],
    pdf: Mapping[str, object],
) -> dict[str, Callable[[Id[Any]], Callable[[], str | bytes]]]:
    """The bytes' producer of each kind of `export_set`, by the row's subject."""
    context = partial(_list_context, model, unit)
    return {
        "bom": lambda _s: partial(bom_csv, model, unit),
        "plc": lambda _s: partial(plc_csv, model, unit=unit),
        "wires": lambda _s: partial(wires_csv, model, unit=unit),
        "designations": lambda _s: partial(designations_csv, model, unit=unit),
        "cables": lambda _s: partial(cables_csv, model, unit=unit),
        "cores": lambda _s: partial(cores_csv, model, unit=unit),
        "overview": lambda _s: partial(
            overview_html, _overview(model)[0], findings=findings, changes=changes
        ),
        "terminals": lambda s: partial(terminal_csv_of, model, s, unit=unit, context=context(s)),
        "connectors": lambda s: partial(connectors_csv_of, model, s, unit=unit, context=context(s)),
        "wago": lambda s: partial(modules_xml_of, model, s, unit=unit),
        "pdf": lambda s: partial(_compile_pdf, model, drawings, s, svgs, fonts, pdf=pdf),
    }


def _ledger(  # noqa: PLR0913 -- one parameter per input of the exports, all keyword
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    svgs: dict[str, str],
    unit: Id[ModelUnit] | None,
    *,
    names_only: bool = False,
    findings: tuple[Finding, ...] = (),
    changes: ListingDiff | None = None,
    timer: Timer | None = None,
    fonts: tuple[Path, ...] = (),
    pdf: Mapping[str, object],
) -> _ExportLedger:
    ledger = _ExportLedger(model, names_only=names_only, timer=timer)
    made = _producers(model, drawings, svgs, unit, findings, changes, fonts, pdf)
    for row in export_set(model, unit):
        ledger.add(
            row.export_kind,
            row.name,
            row.subject,
            partial(_produce, made[row.export_kind], cast("Id[Any]", row.subject)),
            hint=row.hint,
        )
    return ledger


def _exports(  # noqa: PLR0913 -- one keyword per input of the exports, as `_ledger`
    model: Model,
    drawings: Mapping[Id[Page], Drawing],
    svgs: dict[str, str],
    *,
    unit: Id[ModelUnit] | None = None,
    findings: tuple[Finding, ...] = (),
    changes: ListingDiff | None = None,
    timer: Timer | None = None,
    fonts: tuple[Path, ...] = (),
    pdf: Mapping[str, object],
) -> dict[str, bytes]:
    """Every export of `model` by name: `unit` restricts them to that unit; no netlist."""
    return _ledger(
        model,
        drawings,
        svgs,
        unit,
        findings=findings,
        changes=changes,
        timer=timer,
        fonts=fonts,
        pdf=pdf,
    ).exports


def export_names(
    result: BuildResult, *, unit: object = None
) -> dict[tuple[str, Id[Any] | None], str]:
    """Read: the path from out_dir that `write` gives each export of `result`, by `(kind, subject)`.

    A kind is `"bom"`, `"plc"`, `"wires"`, `"designations"`, `"overview"`, `"cables"` or `"cores"`
    (subject `None`), `"terminals"`, `"connectors"` or `"wago"` (the strip, board or rack id), or
    `"pdf"` (the document id). `unit=` is `write`'s. Writes nothing and compiles no PDF; raises what
    `write` raises for a bad `unit` or a name two subjects share (`ExportNameClash`).

    Does not write a file, compile a PDF or run `check`.
    """
    model = result.model
    return _ledger(
        model, {}, {}, _resolve_unit(model, unit), names_only=True, pdf=result.settings.pdf
    ).names


def _remove_prefixed(out_dir: Path, name: str) -> None:
    """Delete every top-level file of `out_dir` whose name starts with `name` and `-v`."""
    for path in out_dir.glob(f"{glob.escape(name)}-v*"):
        if path.is_file():
            path.unlink()


def _clean_stale_exports(out_dir: Path, model: Model, unit: Id[ModelUnit] | None) -> None:
    """Delete the stale exports of `out_dir` and `out_dir/data`, no deeper.

    Old bare names, then `-v` globs of the set name and, for a system write, each release name.
    The top level still gets the CSV and XML patterns: flat files of a write before 0197.
    """
    set_names = {export_set_name(model, unit)} - {""}
    if unit is None:
        set_names |= set(release_names(model))
    for folder in (out_dir, out_dir / _DATA_DIR):
        for pattern in stale_patterns():
            for path in folder.glob(pattern):
                if path.is_file():
                    path.unlink()
        for name in sorted(set_names):
            _remove_prefixed(folder, name)


def write(
    result: BuildResult,
    out_dir: Path,
    *,
    unit: object = None,
    intermediates: Path | None = None,
    releases: Path | None = None,
) -> tuple[Path, ...]:
    """Output: write a built model's exports into `out_dir` and return their paths, sorted.

    Writes CSV reports, WAGO XML, overview HTML and one PDF per document; `unit=` restricts them to
    that unit's own set (no `overview.html`). Intermediates (SVGs, netlists, `.typ`
    sources) go only to `intermediates`, if given. `releases` is a release root as `release`'s
    `into`: with a stored release of the system there, `overview.html` marks what changed since it
    (the release at the model's revision, else the previous one); `None` marks nothing. Any
    `ERROR` in `check(result)` raises `BuildErrors`, writes no export, and removes the exports
    an earlier `write` left in `out_dir` and `out_dir/data`; no escape hatch.
    Also raises `ExportNameClash`, `TypeError` or `ValueError` for a bad `unit`.

    Does not write when `check` finds an ERROR; does not touch files in `out_dir` it does not own.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    svgs = _result_svgs(result)
    out_dir.mkdir(parents=True, exist_ok=True)
    if intermediates is not None:
        intermediates.mkdir(parents=True, exist_ok=True)
        _write_intermediates(model, result.drawings, svgs, intermediates, result.settings.pdf)
    findings = _resolved(raw := _raw_findings(result, svgs), model)
    _clean_stale_exports(out_dir, model, resolved_unit)
    errors = errors_of(findings)
    if errors:
        raise BuildErrors(errors, model=model)
    timer = Timer(result.times.steps)
    exports = _exports(
        model,
        result.drawings,
        svgs,
        unit=resolved_unit,
        findings=raw,
        changes=_changes_since(model, releases, resolved_unit),
        timer=timer,
        fonts=font_dirs(result.settings.font),
        pdf=result.settings.pdf,
    )
    if intermediates is not None:
        _put(intermediates / TIMES_FILE, timer.times().as_json().encode("utf-8"))
    return _put_all(out_dir, exports)


def _put_all(out_dir: Path, exports: dict[str, bytes]) -> tuple[Path, ...]:
    """Write each export under `out_dir`; the paths, sorted."""
    paths = [out_dir / name for name in exports]
    for path, data in zip(paths, exports.values(), strict=True):
        _put(path, data)
    return tuple(sorted(paths))


def release(result: BuildResult, into: Path, *, unit: object = None) -> Path:
    """Output: release a unit, or the system, as a frozen baseline under `into`.

    Writes `<into>/<name>/<version>.<revision>/`: the unit's exports as `write` makes them,
    `baseline/` (listing, model, manifest) and, after a first release, `changes.md` and
    `changes.csv`. Runs the same gate as `write` plus the release checks: any `ERROR`
    raises `BuildErrors` and writes nothing. An identical stored listing text returns the
    existing path untouched. Files are built in a temporary sibling and renamed, so a failure
    leaves nothing behind.

    Does not release when `check` finds an ERROR; does not overwrite an identical release.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    svgs = _result_svgs(result)
    l4 = name_findings(model, _l4_findings(model, resolved_unit, into))
    raw_findings = _revision_pins.with_warnings(_raw_findings(result, svgs), l4)
    findings = _resolved(raw_findings, model)
    errors = errors_of((*findings, *l4))
    if errors:
        raise BuildErrors(errors, model=model)

    target_info = _release_target(model, resolved_unit, into)
    target = target_info.path
    parent = target.parent

    new_listing = baseline.listing(model, resolved_unit)
    new_listing_text = baseline.dumps(new_listing)

    stored_text = stored_listing(target)
    if stored_text is not None and baseline.matches(stored_text, new_listing):
        return target

    exports = _exports(
        model,
        result.drawings,
        svgs,
        unit=resolved_unit,
        fonts=font_dirs(result.settings.font),
        pdf=result.settings.pdf,
    )
    baseline_files = {
        BASELINE_FILES["listing"]: new_listing_text.encode("utf-8"),
        BASELINE_FILES["model"]: model_dumps(model).encode("utf-8"),
    }
    if resolved_unit is not None:
        current_numbering = numbering_pins.pins(model, resolved_unit)
        pin_source = _pin_source(target_info, into)
        retired = (
            () if pin_source is None else gone_or_moved(pin_source[1], current_numbering.items)
        )
        numbering_text = numbering_pins.dumps(
            dataclasses.replace(current_numbering, retired=retired)
        )
        baseline_files[BASELINE_FILES["numbering"]] = numbering_text.encode("utf-8")
    previous_listing = _previous_release_listing(target_info)
    if previous_listing is not None:
        listing_diff = baseline.diff(previous_listing, new_listing)
        baseline_files[BASELINE_FILES["changes_md"]] = changes_markdown(listing_diff).encode(
            "utf-8"
        )
        baseline_files[_placed(BASELINE_FILES["changes_csv"])] = changes_csv(listing_diff).encode(
            "utf-8"
        )
    manifest_text = _manifest(
        model,
        resolved_unit,
        exports=exports,
        baseline_files=baseline_files,
        raw_findings=raw_findings,
    )

    parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=parent, prefix=".release-"))
    built = False
    try:
        (tmp_dir / "baseline").mkdir()
        for filename, data in (*exports.items(), *baseline_files.items()):
            _put(tmp_dir / filename, data)
        (tmp_dir / BASELINE_FILES["manifest"]).write_bytes(manifest_text.encode("utf-8"))
        tmp_dir.rename(target)
        built = True
    finally:
        if not built:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    return target


def diff(
    result: BuildResult, baselines: Path, *, unit: object = None, against: str | None = None
) -> str:
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
    if against is not None:
        candidate = target_info.path.parent / against
        text = stored_listing(candidate)
        if text is None:
            msg = f"no release found at {candidate}"
            raise FileNotFoundError(msg)
        a = baseline.loads(text)
    else:
        since = _since_listing(target_info)
        if since is None:
            msg = f"no released revision found under {target_info.path.parent}"
            raise FileNotFoundError(msg)
        a = since
    return changes_markdown(baseline.diff(a, b))


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


def rebaseline(
    result: BuildResult, baselines: Path, *, unit: str | Id[ModelUnit] | None = None
) -> tuple[Path, ...]:
    """Output: re-cut every stored baseline the current rules print differently, once.

    Rewrites `baseline/listing.json` and `baseline/manifest.json` of each release under
    `baselines` that `verify` notes with `BASELINE_RULES_MOVED` or `BASELINE_ROWS_UNCHECKED`,
    children before parents, and returns those folders (`()` when nothing moved). The manifest
    keeps the old digest, listing version and `fransys` in a `rebaselined` record. `unit=None`
    covers every unit and the system with a stored baseline; a unit covers it and the units below.
    Raises `BuildErrors` and writes nothing when a real row changed (`BASELINE_DIFFERS`), a
    baseline is too old, or a release file is not as released.

    Does not write an export, `model.json` or `numbering.json`.
    """
    model = result.model
    plan = plan_rebaseline(model, baselines, _resolve_unit(model, unit))
    if plan.findings:
        raise BuildErrors(_resolved(plan.findings, model), model=model)
    return write_plan(plan)
