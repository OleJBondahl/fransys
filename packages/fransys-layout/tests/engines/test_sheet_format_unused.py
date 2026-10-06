"""WP14 ruling 2: an authored `layout.sheet_format` no `layout.profile` names is reported.

`read_inputs` carries the ids of the unused sheet formats along and turns each into one
`SHEET_FORMAT_UNUSED` warning in `read_findings`, which the engine returns (engine.md 7, decision
layout-0032). All data invented.
"""

from decimal import Decimal

from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.lint.codes import ALL_CODES, SHEET_FORMAT_UNUSED
from fransys_model.kernel import Draft, Origin, Severity, freeze, make_id
from fransys_model.layout import Page, Profile, SheetFormat, layout_of

_ORIGIN = Origin(file="tests/engines/test_sheet_format_unused.py", line=1, note="sheet formats")


def _sheet(name: str) -> SheetFormat:
    return SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet", name)),
        key=("test", "sheet", name),
        name=name,
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )


def _profile(sheet: SheetFormat) -> Profile:
    return Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )


def _cabinet(*sheets: SheetFormat, named: SheetFormat | None = None) -> Draft:
    """The cabinet with `sheets` authored, and a profile naming `named` when it is given."""
    draft = build_cabinet()
    draft.extend(sheets, origin=_ORIGIN)
    if named is not None:
        draft.extend((_profile(named),), origin=_ORIGIN)
    return draft


def _unused(draft: Draft):
    model = freeze(draft)
    _, findings = stage_results(model, read_inputs(model))
    return [finding for finding in findings if finding.code == SHEET_FORMAT_UNUSED]


def test_the_code_is_listed() -> None:
    """It is one of the package's codes, so `ALL_CODES` and its scan test know it."""
    assert SHEET_FORMAT_UNUSED in ALL_CODES


def test_a_sheet_format_with_no_profile_is_unused_and_warned_about() -> None:
    """Authored, named by no profile: the cabinet is drawn on the house sheet, and it says so."""
    sheet = _sheet("orphan")
    (finding,) = _unused(_cabinet(sheet))
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (sheet.id,)
    assert "A3 landscape" in finding.message
    assert "house sheet" in finding.message


def test_a_sheet_format_the_profile_names_is_not_reported() -> None:
    """The can-fail half: the same sheet, named by the profile, is used and gives no warning."""
    sheet = _sheet("used")
    assert _unused(_cabinet(sheet, named=sheet)) == []


def test_no_authored_sheet_format_gives_no_warning() -> None:
    """The cabinet as authored draws on the house sheet and authors no sheet to ignore."""
    assert _unused(_cabinet()) == []


def test_a_second_sheet_format_is_reported_and_names_the_sheet_the_profile_chose() -> None:
    """One profile, two sheets: the other one is unused, and the message names the used sheet."""
    used, other = _sheet("used"), _sheet("other")
    (finding,) = _unused(_cabinet(used, other, named=used))
    assert finding.subjects == (other.id,)
    assert "'used'" in finding.message
    assert "profile" in finding.message


def test_every_unused_sheet_format_gets_its_own_finding_in_handle_order() -> None:
    """Three sheets and no profile: three warnings, one subject each, sorted by handle."""
    sheets = (_sheet("a"), _sheet("b"), _sheet("c"))
    findings = _unused(_cabinet(*sheets))
    assert [finding.subjects for finding in findings] == sorted((s.id,) for s in sheets)


def test_read_inputs_carries_only_the_ids_of_the_unused_sheet_formats() -> None:
    """The reader hands over the ids of the unused sheet formats, sorted, one finding each."""
    used, other, third = _sheet("used"), _sheet("other"), _sheet("third")
    inputs = read_inputs(freeze(_cabinet(used, other, third, named=used)))
    assert inputs.unused_sheet_formats == tuple(sorted((other.id, third.id)))
    assert inputs.sheet_format == used.id


def test_a_profile_with_no_sheet_lays_the_cabinet_out_on_the_house_sheet() -> None:
    """A profile naming no sheet (`None`) and no authored sheet: every page carries no sheet id."""
    draft = build_cabinet()
    draft.extend(
        (Profile(id=make_id(Profile, ("test", "profile")), key=("test", "profile")),),
        origin=_ORIGIN,
    )
    model, _findings = lay_out_schematic(freeze(draft))
    pages = layout_of(model, Page).values()
    assert pages
    assert {page.sheet_format for page in pages} == {None}


def test_the_public_engine_returns_the_warning() -> None:
    """`lay_out_schematic` returns it with every other finding, and lays the cabinet out."""
    sheet = _sheet("orphan")
    model, findings = lay_out_schematic(freeze(_cabinet(sheet)))
    assert [f.code for f in findings].count(SHEET_FORMAT_UNUSED) == 1
    assert model.digests["layout"]
