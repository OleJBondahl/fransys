"""Pipeline: merge drafts, freeze, run passes, findings policy, write files."""

import dataclasses
import glob
import shutil
import tempfile
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable

import fransys_pdf
import fransys_render
import typst
from fransys_el import REF_TINTS
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

from fransys_layout import lay_out_cables, lay_out_overview
from fransys_model.derive import (
    allocate_plc,
    baseline,
    check_side_hints,
    document_export_name,
    document_unit,
    export_name,
    export_ref,
    export_set_name,
    list_context,
    number,
    numbering_pins,
    reference_fragment,
    terminal_items,
    unit_boards,
    unit_release,
    unit_strips,
    units,
)
from fransys_model.derive.numbering_pins import NumberingItem, NumberingPins, name_findings
from fransys_model.derive.order import finding_order_key, findings_in_order
from fransys_model.kernel import (
    Finding,
    Id,
    Severity,
    digest_cached,
    evolve,
    freeze,
    make_id,
    merge,
    require_origin,
)
from fransys_model.kernel import dumps as model_dumps
from fransys_model.vocab import (
    ALL_VALIDATORS,
    AssignedDesignationFacet,
    ReservedDesignationFacet,
    documents,
    items,
    projects,
    unit_name_unresolved,
    unit_releases,
    units_named,
)
lazy from fransys_model.kernel import AuthoringKey, Draft, Model, Origin

from . import _args, _designation_pins, _revision_pins, _subjects
from ._finding_text import described, fix_lines, headed
from ._layout_need import lay_out_if_needed, needs_schematic_layout
from ._release_checks import (
    _baseline_differs_finding,
    _changes_since,
    _l4_findings,
    _pin_source,
    _previous_release_listing,
    _release_target,
    _ReleaseTarget,
    _since_listing,
)
from ._release_files import release_file_findings
from ._release_manifest import _manifest
from ._release_reader import stored_listing
from ._times import TIMES_FILE, BuildTimes, Timer
from .documents import engine_subject

if TYPE_CHECKING:
    from fransys_model.derive.baseline import ListingDiff
    from fransys_model.vocab import Item, UnitRelease
    from fransys_model.vocab import Unit as ModelUnit

_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}

# CSV and XML exports live in `<out_dir>/data/`; PDFs, `overview.html` and `changes.md` stay on top.
_DATA_DIR = "data"
_DATA_SUFFIXES = (".csv", ".xml")


def _placed(name: str) -> str:
    """`name` as its path from `out_dir`: CSV and XML go into `data/`, the rest stay (0197)."""
    return f"{_DATA_DIR}/{name}" if name.endswith(_DATA_SUFFIXES) else name


def _put(path: Path, data: bytes) -> None:
    """Write `data` to `path`, making `data/` when it is the first file there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


# Top-level `out_dir` export names `write` owns: everything else is left alone. The
# three bare names are a unit's own root's exports, beside the `<kind>-*` globs.
_STALE_EXPORT_PATTERNS = (
    "*.pdf",
    "bom.csv",
    "plc.csv",
    "wire*.csv",
    "designations.csv",
    "cables.csv",
    "cores.csv",
    "terminals-*.csv",
    "connectors-*.csv",
    "wago-*.xml",
    "terminals.csv",
    "connectors.csv",
    "wago.xml",
    "overview.html",
)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BuildResult:
    """A frozen, laid-out model plus every finding collected while building it."""

    model: Model
    findings: tuple[Finding, ...]
    times: BuildTimes = dataclasses.field(default=BuildTimes(), compare=False, repr=False)


class BuildErrors(Exception):  # noqa: N818 -- plural on purpose: it carries every error finding
    """Raised by `write` or `release` when their own findings hold an `ERROR`.

    No escape hatch: there is no `allow_errors`, `force` or `draft` parameter anywhere in
    this package, and none will be added. `findings` holds every `ERROR` of the run that
    raised; the exception's own message is each finding, then its fix and guide anchor.
    `write`'s own findings are resolved through `describe` first (`check`'s own contract);
    `release`'s interface-bump findings are never `describe`d -- their `message` is already
    self-contained, naming the unit, revision and differing sections in plain text.
    """

    def __init__(self, findings: tuple[Finding, ...]) -> None:
        """Store every `ERROR` finding of the run that raised, in `check`'s order."""
        self.findings = findings
        super().__init__("\n".join("\n".join([headed(f), *fix_lines(f)]) for f in findings))


class ExportNameClash(Exception):  # noqa: N818 -- the exact name the contract gives it
    """Two subjects resolve to the same export file name in `out_dir`."""


def _export_name_clash(
    name: str, a: Id[Any], b: Id[Any], model: Model, *, hint: str | None = None
) -> ExportNameClash:
    if hint is None:
        message = f"two subjects both resolve to the export name {name!r}"
    else:
        message = (
            f"two units, both instances of release {hint!r}, both export the file {name!r}; "
            "keep one document per release."
        )
    finding = Finding(
        code="EXPORT_NAME_CLASH",
        severity=Severity.ERROR,
        subjects=(a, b),
        message=message,
    )
    return ExportNameClash(described(finding, model))


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


def _has_error(findings: tuple[Finding, ...]) -> bool:
    return any(finding.severity is Severity.ERROR for finding in findings)


def _has_document(model: Model) -> bool:
    return bool(documents(model))


def _current_item_positions(
    model: Model, unit: Id[ModelUnit]
) -> tuple[dict[AuthoringKey, Id[Item]], NumberingPins]:
    """`unit`'s non-terminal items' structural `(key, scope, code)`, before numbering.

    Built for every item, not gated on `own_designation_or_none`: seeding runs before `number()`.
    `text`/`authored` are dummies: `gone_or_moved` reads only key, scope and code.
    """
    terminals = terminal_items(model)
    key_to_item: dict[AuthoringKey, Id[Item]] = {}
    rows = []
    for item in items(model).values():
        if item.unit != unit or item.id in terminals:
            continue
        key, scope, code = numbering_pins.item_position(model, item.id)
        key_to_item[key] = item.id
        rows.append(NumberingItem(key=key, scope=scope, code=code, text="", authored=False))
    rows.extend(_revision_pins.instance_rows(model, unit))
    rows.sort(key=lambda row: row.key)
    return key_to_item, NumberingPins(items=tuple(rows), retired=())


def _seed_assigned_for_unit(
    model: Model,
    source_pins: NumberingPins,
    key_to_item: dict[AuthoringKey, Id[Item]],
    origins: dict[Id[Any], Origin],
) -> list[AssignedDesignationFacet]:
    """One `assigned_designation` facet per unauthored item whose pin still matches its position.

    A pin's key, scope and code must equal the item's current structural position.
    One unit instance's half of `_seed_designation_pins`.
    """
    seeded: list[AssignedDesignationFacet] = []
    for pin_item in source_pins.items:
        if pin_item.authored:
            continue
        item_id = key_to_item.get(pin_item.key)
        if item_id is None:
            continue
        item_record = items(model)[item_id]
        if item_record.tag is not None:
            continue
        _key, scope, code = numbering_pins.item_position(model, item_id)
        if scope != pin_item.scope or code != pin_item.code:
            continue
        facet_key = (*item_record.key, "assigned_designation")
        facet_id = make_id(AssignedDesignationFacet, facet_key)
        seeded.append(
            AssignedDesignationFacet(
                id=facet_id, key=facet_key, subject=item_id, text=pin_item.text
            )
        )
        origins[facet_id] = require_origin(model.origins, item_id)
    return seeded


def _seed_reserved_for_release(
    model: Model,
    release_record: UnitRelease,
    source_pins: NumberingPins,
    structural_current: NumberingPins,
    origins: dict[Id[Any], Origin],
) -> list[ReservedDesignationFacet]:
    """One `reserved_designation` facet per pin gone or moved, once per distinct release.

    `_designation_pins.gone_or_moved` is `release()`'s own detection, reused, not copied.
    """
    seeded: list[ReservedDesignationFacet] = []
    retired = _designation_pins.gone_or_moved(source_pins, structural_current)
    for index, entry in enumerate(retired):
        reserved_key = ("reserved_designation", str(release_record.id), str(index))
        reserved_id = make_id(ReservedDesignationFacet, reserved_key)
        seeded.append(
            ReservedDesignationFacet(
                id=reserved_id,
                key=reserved_key,
                subject=release_record.id,
                scope=entry.scope,
                code=entry.code,
                text=entry.text,
            )
        )
        origins[reserved_id] = require_origin(model.origins, release_record.id)
    return seeded


def _unit_sources(model: Model, releases: Path) -> dict[Id[ModelUnit], NumberingPins]:
    """Each unit instance's pin source (`_pin_source`), for those that have one."""
    found: dict[Id[ModelUnit], NumberingPins] = {}
    for unit in sorted(units(model)):
        record = unit_release(model, unit)
        target = _ReleaseTarget(
            name=record.name, version=record.version, revision=record.revision, path=Path()
        )
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
        release_record = unit_release(model, unit)
        key_to_item, structural_current = _current_item_positions(model, unit)
        new_facets.extend(_seed_assigned_for_unit(model, source_pins, key_to_item, origins))
        new_facets.extend(_revision_pins.seed_tags(model, unit, source_pins, origins))
        if release_record.id not in seeded_releases:
            seeded_releases.add(release_record.id)
            new_facets.extend(
                _seed_reserved_for_release(
                    model, release_record, source_pins, structural_current, origins
                )
            )
    if not new_facets:
        return model
    evolved = evolve(model, put=new_facets, origin=origins[new_facets[0].id])
    merged_origins = frozendict({**evolved.origins, **origins})
    return dataclasses.replace(evolved, origins=merged_origins)


def build(*drafts: Draft | _args.Design, releases: Path | None = None) -> BuildResult:
    """Output: merge, freeze and lay out drafts or a `Design` into a `BuildResult`.

    Runs PLC allocation, numbering, every validator and layout, collecting each pass's findings.
    The schematic lays out only when no `ERROR` was found and a `Document` keeps a SCHEMATIC
    page; a layout `SymbolPortError` becomes one `SYMBOL_PORT_MISSING` `ERROR`. `releases` seeds
    numbering pins from that release root; `None` numbers freely. Raises `FreezeError` on a
    structural problem in the merged draft.

    Does not write files, run `check` or raise on findings; does not seed pins when `releases`
    is `None`.
    """
    timer = Timer()
    model = timer.run("merge and freeze", _frozen, drafts)
    model, plc_findings = timer.run("PLC allocation", allocate_plc, model)
    model, number_findings = timer.run("numbering", _numbered, model, releases)
    found = timer.run("validators", _validated, model, (*plc_findings, *number_findings))
    if _has_error(found) or not _has_document(model):
        return BuildResult(
            model=model, findings=_by_code_in_reader_order(found, model), times=timer.times()
        )
    model, layout_findings = timer.run("schematic layout", lay_out_if_needed, model)
    model, cable_findings = timer.run("cable layout", lay_out_cables, model)
    found = (*found, *layout_findings, *cable_findings)
    return BuildResult(
        model=model, findings=_by_code_in_reader_order(found, model), times=timer.times()
    )


def _frozen(drafts: tuple[Draft | _args.Design, ...]) -> Model:
    """The drafts merged and frozen."""
    return freeze(merge(*_args.drafts_of(drafts)))


def _numbered(model: Model, releases: Path | None) -> tuple[Model, tuple[Finding, ...]]:
    """`model` numbered with pins seeded from `releases`, and the numbering findings."""
    sources = {} if releases is None else _unit_sources(model, releases)
    model, findings = number(_seed_designation_pins(model, sources))
    return model, (*findings, *_revision_pins.new_findings(model, sources))


def _validated(model: Model, earlier: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """`earlier` and every validator's findings, each named."""
    found = [finding for validator in ALL_VALIDATORS for finding in validator(model)]
    found.extend(check_side_hints(model))
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


def _draw_svgs(model: Model) -> dict[str, str]:
    """Page key to SVG text of `fransys_render`'s pages and cable blocks; only with a document.

    A cable block is keyed by `cable_block_key`, a schematic page by its page id.
    Built once per write/check, reused by `_check`, `_write_intermediates`, `_exports`.
    """
    pages: dict[str, str] = (
        dict(fransys_render.pages(model, tints=REF_TINTS)) if needs_schematic_layout(model) else {}
    )
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


def _svgs(model: Model) -> dict[str, str]:
    """`_draw_svgs(model)` memoised on `model.digest`, last model only (decision 0054); fresh dict.

    `check`, `write` and `release` are its only callers and treat the dict as read-only;
    the copy keeps that safe by contract.
    """
    return dict(_svgs_cache(model))


def _result_svgs(result: BuildResult) -> dict[str, str]:
    """The drawing of a laid-out `result` (no `ERROR`, a `Document`); `{}` otherwise."""
    laid_out = not _has_error(result.findings) and _has_document(result.model)
    return _svgs(result.model) if laid_out else {}


def _raw_findings(result: BuildResult, svgs: dict[str, str]) -> tuple[Finding, ...]:
    """Every finding of a build before `describe`.

    `describe` embeds `file:line (key)`, not reproducible across checkouts, so `release`'s manifest
    reads each WARNING's raw `message` from here.
    """
    model = result.model
    raw = list(result.findings)
    for board in _subjects.boards(model):
        raw.extend(kicad_check(model, board))
    if not _has_error(result.findings):
        raw.extend(_overview(model)[1])
    if not _has_error(result.findings) and _has_document(model):
        raw.extend(fransys_pdf.check(model, svgs))
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


def _file_safe(page_key: str) -> str:
    """`page_key` as a filesystem-safe name fragment.

    `:` opens an NTFS alternate stream on Windows, so a naive write silently produces no `.svg`.
    """
    return page_key.replace(":", "-")


def _write_intermediates(model: Model, svgs: dict[str, str], intermediates: Path) -> None:
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
    for document_id, record in documents(model).items():
        source_text = fransys_pdf.source(model, document_id, svgs)
        (intermediates / f"{record.key[1]}.typ").write_bytes(source_text.encode("utf-8"))


class _ExportLedger:
    """Export names, and with `names_only=False` their bytes, refusing a name two subjects want.

    `names` maps `(kind, subject)` to the name: one traversal gives `write` its bytes and
    `export_names` its names, so the naming rule has one home.
    """

    def __init__(
        self, model: Model, *, names_only: bool = False, timer: Timer | None = None
    ) -> None:
        self._model = model
        self._timer = timer or Timer()
        self._names_only = names_only
        self.exports: dict[str, bytes] = {}
        self.names: dict[tuple[str, Id[Any] | None], str] = {}
        self._subjects_by_name: dict[str, Id[Any] | None] = {}

    def add(
        self,
        kind: str,
        name: str,
        subject: Id[Any] | None,
        data: Callable[[], str | bytes],
        *,
        hint: str | None = None,
    ) -> None:
        name = _placed(name)
        held = self._subjects_by_name.get(name)
        if held is not None and subject is not None and held != subject:
            raise _export_name_clash(name, held, subject, self._model, hint=hint)
        self.names[(kind, subject)] = name
        self._subjects_by_name[name] = subject
        if not self._names_only:
            made = self._timer.run(name, data)
            self.exports[name] = made.encode("utf-8") if isinstance(made, str) else made


def _compile_pdf(model: Model, document_id: Id[Any], svgs: dict[str, str]) -> bytes:
    """One document's Typst source, compiled to PDF bytes (decision pdf-0001).

    Touches font files, so only here, never in pure `fransys_pdf`; passes no `timestamp=`:
    the date is the source's `#set document(date: ...)`; Typst reads one only for `auto` (0030).
    """
    source_text = fransys_pdf.source(model, document_id, svgs)
    compiler = typst.Compiler(font_paths=[fransys_pdf.font_dir()], ignore_system_fonts=True)
    compiled = compiler.compile(input=source_text.encode("utf-8"))
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


def _add_system_exports(
    ledger: _ExportLedger,
    model: Model,
    unit: Id[ModelUnit] | None,
    findings: tuple[Finding, ...] = (),
    changes: ListingDiff | None = None,
) -> None:
    """The CSV reports, and with `unit=None` the two whole-system views."""
    made: dict[str, tuple[str, Callable[[], str]]] = {
        "bom": ("csv", partial(bom_csv, model, unit)),
        "plc": ("csv", partial(plc_csv, model, unit=unit)),
        "wires": ("csv", partial(wires_csv, model, unit=unit)),
        "designations": ("csv", partial(designations_csv, model, unit=unit)),
        "cables": ("csv", partial(cables_csv, model, unit=unit)),
        "cores": ("csv", partial(cores_csv, model, unit=unit)),
    }
    if unit is None:
        made["overview"] = (
            "html",
            partial(overview_html, _overview(model)[0], findings=findings, changes=changes),
        )
    for kind, (extension, produce) in made.items():
        ledger.add(kind, export_name(model, unit, extension, kind=kind), None, produce)


def _list_context(model: Model, unit: Id[ModelUnit] | None, subject: Id[Any]) -> Id[Any] | None:
    """The list context a CSV prints its ends in (model-0054 section 4); none in `out/all/`."""
    return None if unit is None else list_context(model, subject)


def _item_subjects(
    model: Model, unit: Id[ModelUnit] | None
) -> tuple[tuple[Id[Any], ...], tuple[Id[Any], ...], tuple[Id[Any], ...]]:
    """The strips, boards and racks of `unit` (all of them with `unit=None`)."""
    strips, boards, racks = _subjects.strips(model), _subjects.boards(model), _subjects.racks(model)
    if unit is None:
        return strips, boards, racks
    all_items = items(model)
    return (
        unit_strips(model, unit),
        unit_boards(model, unit),
        tuple(r for r in racks if all_items[r].unit == unit),
    )


def _add_item_exports(ledger: _ExportLedger, model: Model, unit: Id[ModelUnit] | None) -> None:
    """One terminal CSV per strip, one connector CSV per board, one WAGO XML per rack."""
    strips, boards, racks = _item_subjects(model, unit)
    for strip in strips:
        fragment = export_ref(model, strip, unit)
        name = export_name(model, unit, "csv", kind="terminals", fragment=fragment)
        context = _list_context(model, unit, strip)
        produce = partial(terminal_csv_of, model, strip, unit=unit, context=context)
        ledger.add("terminals", name, strip, produce)
    for board in boards:
        fragment = export_ref(model, board, unit)
        name = export_name(model, unit, "csv", kind="connectors", fragment=fragment)
        context = _list_context(model, unit, board)
        produce = partial(connectors_csv_of, model, board, unit=unit, context=context)
        ledger.add("connectors", name, board, produce)
    for rack in racks:
        fragment = export_ref(model, rack, unit)
        name = export_name(model, unit, "xml", kind="wago", fragment=fragment)
        ledger.add("wago", name, rack, partial(modules_xml_of, model, rack, unit=unit))


def _add_document_exports(
    ledger: _ExportLedger, model: Model, svgs: dict[str, str], unit: Id[ModelUnit] | None
) -> None:
    """One PDF per document of `unit` (every document with `unit=None`), by `document_id`."""
    # The "keep one document per release" hint fires only when the already-held name also came
    # from a unit-subject document of the SAME release (`Unit.release` id, never a name-string
    # compare), not for an ordinary clash that merely shares a `UnitRelease.name`-shaped string.
    document_entries = documents(model).items()
    if unit is not None:
        document_entries = [(i, r) for i, r in document_entries if document_unit(model, r) == unit]
    all_units = units(model)
    release_by_name: dict[str, Id[Any]] = {}
    for document_id, record in document_entries:
        name = document_export_name(model, unit, record)
        hint = None
        document_own_unit = document_unit(model, record)
        if document_own_unit is not None:
            release_id = all_units[document_own_unit].release
            if release_by_name.get(name) == release_id:
                hint = export_set_name(model, document_own_unit)
            release_by_name[name] = release_id
        ledger.add(
            "pdf", name, document_id, partial(_compile_pdf, model, document_id, svgs), hint=hint
        )


def _ledger(  # noqa: PLR0913 -- one parameter per input of the exports, all keyword
    model: Model,
    svgs: dict[str, str],
    unit: Id[ModelUnit] | None,
    *,
    names_only: bool = False,
    findings: tuple[Finding, ...] = (),
    changes: ListingDiff | None = None,
    timer: Timer | None = None,
) -> _ExportLedger:
    ledger = _ExportLedger(model, names_only=names_only, timer=timer)
    _add_system_exports(ledger, model, unit, findings, changes)
    _add_item_exports(ledger, model, unit)
    _add_document_exports(ledger, model, svgs, unit)
    return ledger


def _exports(  # noqa: PLR0913 -- one keyword per input of the exports, as `_ledger`
    model: Model,
    svgs: dict[str, str],
    *,
    unit: Id[ModelUnit] | None = None,
    findings: tuple[Finding, ...] = (),
    changes: ListingDiff | None = None,
    timer: Timer | None = None,
) -> dict[str, bytes]:
    """Every export of `model` by name: `unit` restricts them to that unit; no netlist."""
    return _ledger(model, svgs, unit, findings=findings, changes=changes, timer=timer).exports


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
    return _ledger(model, {}, _resolve_unit(model, unit), names_only=True).names


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
        set_names |= {release.name for release in unit_releases(model).values()}
    for folder in (out_dir, out_dir / _DATA_DIR):
        for pattern in _STALE_EXPORT_PATTERNS:
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
    `ERROR` in `check(result)` raises `BuildErrors` and leaves `out_dir` without an export,
    whole-model, with no escape hatch.
    Also raises `ExportNameClash`, `TypeError` or `ValueError` for a bad `unit`.

    Does not write when `check` finds an ERROR; does not touch files in `out_dir` it does not own.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    svgs = _result_svgs(result)
    out_dir.mkdir(parents=True, exist_ok=True)
    if intermediates is not None:
        intermediates.mkdir(parents=True, exist_ok=True)
        _write_intermediates(model, svgs, intermediates)
    findings = _resolved(raw := _raw_findings(result, svgs), model)
    _clean_stale_exports(out_dir, model, resolved_unit)
    errors = tuple(finding for finding in findings if finding.severity is Severity.ERROR)
    if errors:
        raise BuildErrors(errors)
    timer = Timer(result.times.steps)
    exports = _exports(
        model,
        svgs,
        unit=resolved_unit,
        findings=raw,
        changes=_changes_since(model, releases, resolved_unit),
        timer=timer,
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
    errors = tuple(finding for finding in (*findings, *l4) if finding.severity is Severity.ERROR)
    if errors:
        raise BuildErrors(errors)

    target_info = _release_target(model, resolved_unit, into)
    target = target_info.path
    parent = target.parent

    new_listing = baseline.listing(model, resolved_unit)
    new_listing_text = baseline.dumps(new_listing)

    stored_text = stored_listing(target)
    if stored_text is not None and baseline.matches(stored_text, new_listing):
        return target

    exports = _exports(model, svgs, unit=resolved_unit)
    baseline_files = {
        "baseline/listing.json": new_listing_text.encode("utf-8"),
        "baseline/model.json": model_dumps(model).encode("utf-8"),
    }
    if resolved_unit is not None:
        current_numbering = numbering_pins.pins(model, resolved_unit)
        pin_source = _pin_source(target_info, into)
        retired = (
            ()
            if pin_source is None
            else _designation_pins.gone_or_moved(pin_source[1], current_numbering)
        )
        numbering_text = numbering_pins.dumps(
            dataclasses.replace(current_numbering, retired=retired)
        )
        baseline_files["baseline/numbering.json"] = numbering_text.encode("utf-8")
    previous_listing = _previous_release_listing(target_info)
    if previous_listing is not None:
        listing_diff = baseline.diff(previous_listing, new_listing)
        baseline_files["changes.md"] = changes_markdown(listing_diff).encode("utf-8")
        baseline_files[_placed("changes.csv")] = changes_csv(listing_diff).encode("utf-8")
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
        (tmp_dir / "baseline" / "manifest.json").write_bytes(manifest_text.encode("utf-8"))
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

    Compares the rebuilt listing digest with the stored one under `baselines`, for every unit
    and for the system when the model holds a `Project`. The model digest is never compared.
    Also re-hashes every release file: `RELEASE_FILE_CHANGED`, `RELEASE_FILE_MISSING`.
    Meant for a consumer's test, wherever they want it.

    Does not write files, release or gate `write`; does not report a unit with no stored baseline.
    """
    model = result.model
    subjects: tuple[Id[ModelUnit] | None, ...] = (
        *sorted(units(model)),
        *((None,) if projects(model) else ()),
    )
    findings: list[Finding] = []
    for unit in subjects:
        target = _release_target(model, unit, baselines)
        stored_text = stored_listing(target.path)
        if stored_text is None:
            continue
        differs = _baseline_differs_finding(model, unit, target, stored_text)
        if differs is not None:
            findings.append(differs)
    findings.extend(release_file_findings(baselines))
    return tuple(findings)
