"""The files `write` puts out: pdf source, producers, ledger, export names, stale clean."""

import dataclasses
import glob
from functools import partial
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Callable, Mapping
lazy from pathlib import Path

import fransys_pdf
import fransys_render
import typst
from fransys_kicad import netlist as kicad_netlist
from fransys_overview import html as overview_html
from fransys_reports import (
    bom_csv,
    cables_csv,
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
from fransys_layout import DiagramLayout
from fransys_layout.symbols import text_room_on
from fransys_model.derive import (
    document_stems,
    errors_of,
    export_form_of,
    export_set,
    export_set_name,
    list_context,
    pdf_texts,
    reference_fragment,
    release_names,
    stale_patterns,
    unit_name_unresolved,
    units_named,
)
from fransys_model.derive.page_nav import reference_links
from fransys_model.kernel import (
    Finding,
    Id,
)
from fransys_model.layout import sheet_format_of
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab import Unit as ModelUnit

from . import _args, _subjects
from ._export_ledger import _export_name_clash, _ExportLedger
from ._layout_need import diagram_sheets_of
from ._link_boxes import link_boxes
from ._release_checks import (
    _changes_since,
)
from ._settings_library import font_dirs
from ._times import TIMES_FILE, Timer
from .documents import engine_subject
from .errors import FransysError
from .pipeline import BuildFailedError, BuildResult, _Drawn, _library, _overview, _raw_findings, _Read, _resolved, _result_svgs, _sheets
lazy from .settings import Settings

if TYPE_CHECKING:
    from fransys_model.derive.baseline import ListingDiff


def _put(path: Path, data: bytes) -> None:
    """Write `data` to `path`, making `data/` when it is the first file there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _file_safe(page_key: str) -> str:
    """`page_key` as a filesystem-safe name fragment.

    `:` opens an NTFS alternate stream on Windows, so a naive write silently produces no `.svg`.
    """
    return page_key.replace(":", "-")


def _refuse_repeated_stems(model: Model, stems: tuple[tuple[Id[Any], str], ...]) -> None:
    """Two documents with one `.typ` stem would overwrite each other: refuse, naming both."""
    held: dict[str, Id[Any]] = {}
    for document_id, stem in stems:
        if stem in held:
            name = f"{stem}.typ"
            raise _export_name_clash(name, held[stem], document_id, model)
        held[stem] = document_id


def _write_intermediates(drawn: _Drawn, svgs: dict[str, str], intermediates: Path, pdf: Mapping[str, object]) -> None:
    """Page SVGs, netlists and Typst source that never reach `out_dir`; written before the gate.

    A half-finished design still draws; an errored build has no pages (decision 0028, model-0077).
    Typst is not compiled here (fonts: `_exports`); pages come from the built `svgs`.
    """
    model = drawn.model
    for page_key, svg in svgs.items():
        (intermediates / f"{_file_safe(page_key)}.svg").write_bytes(svg.encode("utf-8"))
    for board in _subjects.boards(model):
        text = kicad_netlist(model, board)
        (intermediates / f"netlist-{reference_fragment(model, board)}.net").write_bytes(text.encode("utf-8"))
    stems = document_stems(model)
    _refuse_repeated_stems(model, stems)
    for document_id, stem in stems:
        source_text = _pdf_source(drawn, document_id, svgs, pdf)
        (intermediates / f"{stem}.typ").write_bytes(source_text.encode("utf-8"))


def _pdf_source(drawn: _Drawn, document_id: Id[Any], svgs: Mapping[str, str], pdf: Mapping[str, object]) -> str:
    """One document's Typst source, with the numbers of the `[pdf]` settings."""
    model, library = drawn.model, drawn.library
    known = frozenset(drawn.drawings)
    boxes = link_boxes(model, drawn.drawings, library)
    return fransys_pdf.source(
        model,
        document_id,
        svgs,
        _sheets(drawn),
        fransys_render.bridge_pieces(library),
        links={page: reference_links(model, page, known, boxes) for page in known},
        diagrams=diagram_sheets_of(drawn.diagrams),
        pdf=cast("Mapping[str, float]", pdf),
        **pdf_texts(model),
    )


def _compile_pdf(drawn: _Drawn, document_id: Id[Any], settings: Settings) -> bytes:
    """One document's Typst source, compiled to PDF bytes (decision pdf-0001).

    Touches font files, so only here, never in pure `fransys_pdf`; passes no `timestamp=`: the
    date is the source's `#set document(date: ...)` (0030).
    """
    source_text = _pdf_source(drawn, document_id, drawn.page_svgs, settings.pdf)
    fonts = font_dirs(settings.font)
    compiler = typst.Compiler(font_paths=list(fonts) or [electrical_symbols.font_dir()], ignore_system_fonts=True)
    try:
        compiled = compiler.compile(input=source_text.encode("utf-8"))
    except typst.TypstError as error:
        overflow = fransys_pdf.cover_overflow_finding(document_id, str(error))
        if overflow is None:
            raise
        raise BuildFailedError(_resolved((overflow,), drawn.model), model=drawn.model) from error
    # typst.Compiler.compile's stub types every call `bytes | list[bytes] | None` because the
    # union also covers `output=<path>` (writes to disk, returns `None`) and multi-file input
    # (returns `list[bytes]`); this call passes neither, so it always returns `bytes` (confirmed
    # by compiling, decision pdf-0001's addendum).
    return cast("bytes", compiled)


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
        raise FransysError(unit_name_unresolved(model, unit))
    if isinstance(unit, Id | _args.Scope):
        return _subjects.unit_of(unit, "write()'s unit=", "a unit Id instead")
    msg = f"unit= must be a release name or None, not {type(unit).__name__}"
    raise FransysError(msg)


def _list_context(model: Model, unit: Id[ModelUnit] | None, subject: Id[Any]) -> Id[Any] | None:
    """The list context a CSV prints its ends in (model-0054 section 4); none in `out/all/`."""
    return None if unit is None else list_context(model, subject)


def _produce(make: Callable[[Id[Any]], Callable[[], str | bytes]], subject: Id[Any]) -> str | bytes:
    return make(subject)()


@dataclasses.dataclass(frozen=True, slots=True)
class _Export:
    """What one build's exports read: `drawn` (its `page_svgs` all the svgs), settings and scope."""

    drawn: _Drawn
    settings: Settings
    within: Id[ModelUnit] | None = None
    findings: tuple[Finding, ...] = ()
    changes: ListingDiff | None = None
    timer: Timer | None = None


def _producers(job: _Export) -> dict[str, Callable[[Id[Any]], Callable[[], str | bytes]]]:
    """The bytes' producer of each kind of `export_set`, by the row's subject."""
    model, unit = job.drawn.model, job.within
    context = partial(_list_context, model, unit)
    return {
        "bom": lambda _s: partial(bom_csv, model, unit),
        "plc": lambda _s: partial(plc_csv, model, unit=unit),
        "wires": lambda _s: partial(wires_csv, model, unit=unit),
        "designations": lambda _s: partial(designations_csv, model, unit=unit),
        "cables": lambda _s: partial(cables_csv, model, unit=unit),
        "cores": lambda _s: partial(cores_csv, model, unit=unit),
        "overview": lambda _s: partial(
            overview_html,
            _overview(_Read(model, job.drawn.library))[0],
            text_height=text_room_on(model, sheet_format_of(model, None), job.drawn.library),
            findings=job.findings,
            changes=job.changes,
        ),
        "terminals": lambda s: partial(terminal_csv_of, model, s, unit=unit, context=context(s)),
        "connectors": lambda s: partial(connectors_csv_of, model, s, unit=unit, context=context(s)),
        "wago": lambda s: partial(modules_xml_of, model, s, unit=unit),
        "pdf": lambda s: partial(_compile_pdf, job.drawn, s, job.settings),
    }


def _ledger(job: _Export, *, names_only: bool = False) -> _ExportLedger:
    model, unit = job.drawn.model, job.within
    ledger = _ExportLedger(model, names_only=names_only, timer=job.timer)
    made = _producers(job)
    for row in export_set(model, unit):
        ledger.add(
            row.export_kind,
            row.name,
            row.subject,
            partial(_produce, made[row.export_kind], cast("Id[Any]", row.subject)),
            hint=row.hint,
        )
    return ledger


def _exports(job: _Export) -> dict[str, bytes]:
    """Every export of the model by name: `job.within` restricts them to that unit; no netlist."""
    return _ledger(job).exports


def export_names(result: BuildResult, *, unit: object = None) -> dict[tuple[str, Id[Any] | None], str]:
    """Read: the path from out_dir that `write` gives each export of `result`, by `(kind, subject)`.

    A kind is `"bom"`, `"plc"`, `"wires"`, `"designations"`, `"overview"`, `"cables"` or `"cores"`
    (subject `None`), `"terminals"`, `"connectors"` or `"wago"` (the strip, board or rack id), or
    `"pdf"` (the document id). `unit=` is `write`'s. Writes nothing and compiles no PDF; raises what
    `write` raises for a bad `unit` or a name two subjects share (`ExportNameClashError`).

    Does not write a file, compile a PDF or run `check`.
    """
    model = result.model
    drawn = _Drawn(model, {}, DiagramLayout(diagrams=()), _library(result), {})
    return _ledger(_Export(drawn, result.settings, _resolve_unit(model, unit)), names_only=True).names


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
    for folder in (out_dir, out_dir / export_form_of(model).data_dir):
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
    `ERROR` in `check(result)` raises `BuildFailedError`, writes no export, and removes the exports
    an earlier `write` left in `out_dir` and `out_dir/data`; no escape hatch.
    Also raises `ExportNameClashError`, `TypeError` or `ValueError` for a bad `unit`.

    Does not write when `check` finds an ERROR; does not touch files in `out_dir` it does not own.
    """
    model = result.model
    resolved_unit = _resolve_unit(model, unit)
    svgs = _result_svgs(result)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_result_intermediates(result, svgs, intermediates)
    findings = _resolved(raw := _raw_findings(result, svgs), model)
    _clean_stale_exports(out_dir, model, resolved_unit)
    _raise_on_errors(findings, model)
    timer = Timer(result.times.steps)
    exports = _exports(
        _Export(
            _Drawn(model, result.drawings, result.diagrams, _library(result), svgs),
            result.settings,
            resolved_unit,
            raw,
            _changes_since(model, releases, resolved_unit),
            timer,
        )
    )
    if intermediates is not None:
        _put(intermediates / TIMES_FILE, timer.times().as_json().encode("utf-8"))
    return _put_all(out_dir, exports)


def _write_result_intermediates(result: BuildResult, svgs: dict[str, str], intermediates: Path | None) -> None:
    """Write the build's intermediates under `intermediates`, when given."""
    if intermediates is None:
        return
    intermediates.mkdir(parents=True, exist_ok=True)
    drawn = _Drawn(result.model, result.drawings, result.diagrams, _library(result), result.page_svgs)
    _write_intermediates(drawn, svgs, intermediates, result.settings.pdf)


def _raise_on_errors(findings: tuple[Finding, ...], model: Model) -> None:
    """Raise `BuildFailedError` when `findings` hold an ERROR."""
    errors = errors_of(findings)
    if errors:
        raise BuildFailedError(errors, model=model)


def _put_all(out_dir: Path, exports: dict[str, bytes]) -> tuple[Path, ...]:
    """Write each export under `out_dir`; the paths, sorted."""
    paths = [out_dir / name for name in exports]
    for path, data in zip(paths, exports.values(), strict=True):
        _put(path, data)
    return tuple(sorted(paths))
