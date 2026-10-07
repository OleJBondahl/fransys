"""D2 equality: the stage's measured text equals the model's own reader (decision layout-0037).

Proves `fransys_model.derive.drawing_text`'s readers reproduce, from the persisted
`layout.*` records of a laid-out model alone, the text `fransys_layout` measured when it
sized a label's slot or a marker's box.

The wide cabinet golden (`tests/golden/cabinet_laid_out.json`, ROADMAP WP14) has no severed
cut, so none of its markers comes from `links`; under the deep dive it does hold D9 star
markers and D7 `CROSS_REFERENCE` labels (each contact's line and each coil's contact image).
Its marker and cross-reference counts are asserted explicitly. `label_text`'s TAG and MARKING
branches are checked against the exact text the stage measured for each label's box,
and the D7 labels against the positions of the coil and its contacts, read from the persisted
placements.

The narrow cabinet golden (`tests/golden/cabinet_narrow_laid_out.json`, the 158 mm sheet of
`docs/archive/specs/2026-09-22-cross-reference-partner.md` X5, moved from the spec's 150 by
model-0040 -- see `_NARROW_WIDTH_MM` below) is where `marker_text` is checked for every marker
kind: one severed cut (two `layout.link_marker` records) and the D9 star markers. Its
`CROSS_REFERENCE` labels are the D7 ones. The K8 `LATCH` net-group cut that once gave two tag
echoes no longer arises at any sheet width (60 to 336 mm scanned): both K8 functions stand on
one page (D2, D7).

`page_title` has no equivalent here: the engine computes a `PagePlan.title` while planning
pages (`fransys_layout.stages.types.PagePlan`), but nothing carries it past that stage --
no `StageResults` field, no persisted `layout.page` field (model layout-namespace.md, the
`layout.page` row: the title is rendered from the groups). There is nothing already-computed
to compare `page_title(model, page)` against without re-running `partition` by hand, so this
module does not attempt it; `page_title`'s only coverage is the hand-built model test in
`fransys-model` (decision model-0032). Render will build a page's title from the reader.
"""

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from layout_cabinet import build_cabinet
from samples import built_links

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.engines.schematic.read.labels import label_requests
from fransys_layout.engines.schematic.read.reading import location_path
from fransys_layout.geometry import text_width
from fransys_layout.stages import resolve
from fransys_layout.stages.types import LabelKind as StageLabelKind
from fransys_model.derive.drawing_text import (
    frame_column,
    frame_row,
    label_text,
    marker_text,
    position_text,
)
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import (
    Label,
    LinkMarker,
    Page,
    Profile,
    SheetFormat,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.layout import LabelKind as ModelLabelKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.engines.schematic.read import StageInputs
    from fransys_layout.stages.types import Layout
    from fransys_layout.stages.types import LinkMarker as StageLinkMarker
    from fransys_layout.stages.types import Profile as StageProfile
    from fransys_model.kernel import Draft, Id, Model

# The narrow sheet width spec X5 (`docs/archive/specs/2026-09-22-cross-reference-partner.md`)
# requires: a width that gives all three required contents at once (a severed cut, a
# `CROSS_REFERENCE` label, a net-group cut). 158, not the spec's original 150: model-0040
# (spec B1) draws board `A1`'s `edge` connector, which shifts where this cabinet splits;
# 158 is the narrowest width that still gives all three (Q4, measured at 1 mm resolution),
# and it is well within the 118-171 mm band `fransys-render`'s tests need (they load this
# package's golden by path and hardcode a marker position and a page count; model-0040 has
# the measured table); see `test_usecases.py`'s own `_NARROW_WIDTH_MM`, duplicated here, for
# the widths that now give none of the three.
_NARROW_WIDTH_MM = 158

# `_narrow_sheet_draft` is a second, independent construction of the same sheet/profile
# `test_usecases._on_sheet` builds (see its docstring): `_narrow_layout` checks the rebuilt
# model's digest against the committed golden's before either loop below trusts it, so the two
# constructions drifting apart (a changed width literal, a changed `frame_columns`) fails loudly
# here instead of silently testing a layout that is no longer the one in `tests/golden/`.
_NARROW_DIGEST_GOLDEN = (
    Path(__file__).resolve().parent.parent / "golden" / "cabinet_narrow_layout_digest.txt"
)

# `pytest usecases --regenerate-golden` runs this module before `test_usecases.py` (alphabetical
# file order: "d" < "u"), so `_narrow_layout`'s read of `_NARROW_DIGEST_GOLDEN` below would race
# `test_usecases.py`'s own regeneration of that same file: reading it before that later test
# rewrites it, and failing on a stale value a single regenerating run would otherwise leave
# correct. The two tests that call `_narrow_layout` skip themselves under the flag instead.


@pytest.fixture
def regenerate(request: pytest.FixtureRequest) -> bool:
    """True under `--regenerate-golden`.

    Duplicated from `test_usecases.py`'s fixture of the same name: this module cannot import
    that one (see `_narrow_sheet_draft`'s docstring).
    """
    return bool(request.config.getoption("--regenerate-golden"))


# The wide golden's TAG + MARKING label count (WP14's cabinet): checked explicitly so
# a change to the fixture's shape fails this test loudly instead of silently checking fewer
# labels. 66 = 40 + 26, counted from the fixture (no wire label stands on a page, V8):
# - MARKING 40: every port of a drawn non-terminal function (D5 shows every port of the
#   lamp's box): S0 4, K1 10, K2 10, Q1/Q2/S1/S2 2 each, F1 2, H1 2, K8 4. Board `A1`'s idle
#   `edge` connector is not drawn (D8).
# - TAG 26: one per drawn non-terminal function (F1, H1, K1 x3, K2 x3, K8 x2, Q1, Q2, S0 x2,
#   S1, S2 = 16) and one per terminal on each page it stands on (X1:1, X1:2, X1:3, X2:1 x2,
#   X3:1, X3:2, X4:1 x2, X4:2 = 10).
_EXPECTED_TAG_MARKING_COUNT = 66

# The wide golden's markers and CROSS_REFERENCE labels. Six markers: one line stub and five star
# markers. HL1 draws `W1` (rails to the lamp `-H1`) as a line, which leaves page 1 in its one stub
# (HL18). The 24 V net keeps four ports (`X2:1` external and the three stop-button ports 11): two
# branches (S0's pin has `X2:1` over it, V4) and the reference on page 1; and a
# turned pair (M12, `references.turned`): K1's aux port 13 faces N and its link to `S0:nc_2:22`
# runs to a device below K1's bottom edge, so it is a reference pair, `S0:nc_2:22` the
# reference and K1:aux:13 the branch. Eight CROSS_REFERENCE labels (D7): a line under each of
# the five contacts (K1 main and aux, K2 main and aux, K8 no_1) and a contact image under each
# of the three coils.
_EXPECTED_WIDE_MARKER_COUNT = 6
_EXPECTED_WIDE_REF_MARKER_COUNT = 2
_EXPECTED_WIDE_CROSS_REFERENCE_COUNT = 8

# The narrow golden's (158 mm) marker counts, checked explicitly for the same reason (spec
# X5's "never iterated silently"): two severed markers (one cut, K1:14 to K2:13, a marker at
# either end) and two D9 star markers (the branch `S1`, `S0` has `X2:1` over its pin (V4), and
# the reference on page 1; HL1 takes the lamp `H1` off the star, `W1` is a line whose two leaving
# ends are two line stubs, HL18), and two more star markers, the turned
# pair of the K1:aux:13 <-> S0:nc_2:22 wire (wire 17): K1's aux stands on page 1 (layout-0049,
# D2) above S0's contact, so the link from K1's N pin runs to a device below it and is a
# reference pair (M12, `references.turned`), not a wire and not a cut.
_EXPECTED_NARROW_SEVERED_MARKER_COUNT = 2
_EXPECTED_NARROW_MARKER_COUNT = 6
_EXPECTED_NARROW_LINE_STUB_COUNT = 2
# ... and the same eight D7 CROSS_REFERENCE labels as the wide golden.
_EXPECTED_NARROW_CROSS_REFERENCE_COUNT = 8

# D7, per coil item of the cabinet: its contacts, in the order the image lists them (main
# contacts first), each with the pin pairs of its terminals ("1-2" is ports 1 and 2). Read
# from the fixture's parts: the contactor's `main` has ports 1-6, its `aux` 13-14; the relay's
# `no_1` 13-14; every contact is normally open, so the images have no NC entry.
_COIL_CONTACTS = {
    "k1": (("main", ("1-2", "3-4", "5-6")), ("aux", ("13-14",))),
    "k2": (("main", ("1-2", "3-4", "5-6")), ("aux", ("13-14",))),
    "k8": (("no_1", ("13-14",)),),
}


def _narrow_sheet_draft() -> Draft:
    """The cabinet on an authored `_NARROW_WIDTH_MM` sheet: `test_usecases._on_sheet`'s build.

    Duplicated, not imported: `tests/usecases/` is not on `sys.path` under
    `--import-mode=importlib` (`tests/conftest.py`, off limits to this task, only appends
    `tests/` itself and `tests/lint/`), so this module cannot `import test_usecases`.
    """
    draft = build_cabinet()
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrower",
        width_mm=_NARROW_WIDTH_MM + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=_NARROW_WIDTH_MM,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = Profile(
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
    draft.extend((sheet, profile), origin=Origin(file=__file__, line=1, note="narrower sheet"))
    return draft


def _placed_position(model: Model, inputs: StageInputs, function: Id[Any], reader: Id[Any]) -> str:
    """`function`'s one placement as `reader` prints it: the cell on its page, else `p<n>:<cell>`.

    The position D7 puts on a contact's cross-reference line and in a coil's contact image.
    Built from the record's page number, x and y with the three shared pure formatters
    (LD5), not from a reader that takes a label.
    """
    placements = layout_of(model, SymbolPlacement).values()
    (placement,) = (one for one in placements if one.function == function)
    (reading,) = (one for one in placements if one.function == reader)
    pages = layout_of(model, Page)
    page = pages[placement.page]
    sheet = inputs.sheet
    column = frame_column(sheet.content_width, sheet.frame_columns, placement.x)
    row = frame_row(sheet.content_height, sheet.frame_rows, placement.y)
    return position_text(page.number, column, row, (), own_page=pages[reading.page].number)


def _check_contact_references(model: Model, inputs: StageInputs, layout: Layout) -> None:
    """D7, on the persisted labels: each contact's line and each coil's contact image.

    The reader's text of a contact's `tag` CROSS_REFERENCE label is its coil's position, and
    of a coil's `contacts` label the "NO | NC" table with one "<pins> <position>" row per
    contact pin pair, main contacts first. Each image's stage box (`layout.labels`, what the
    stage reserved) is as wide as twice its widest measured cell plus the marker padding on
    both sides, and as high as a header, its rows and three paddings: the D2 equality for a
    text the reader rebuilds from the model.
    """
    function_of = {"/".join(record.key): i for i, record in model.tables["function"].items()}
    text_of = {
        (label.function, label.slot): label_text(model, label)
        for label in layout_of(model, Label).values()
        if label.kind is ModelLabelKind.CROSS_REFERENCE
    }
    profile = inputs.profile
    for item, contacts in _COIL_CONTACTS.items():
        coil = function_of[f"cabinet/{item}/fn/coil"]
        rows = []
        for name, pin_pairs in contacts:
            contact = function_of[f"cabinet/{item}/fn/{name}"]
            assert text_of[contact, "tag"] == _placed_position(model, inputs, coil, contact)
            here = _placed_position(model, inputs, contact, coil)
            rows.extend(f"{pins} {here} | " for pins in pin_pairs)
        image = "\n".join(["NO | NC", *rows])
        assert text_of[coil, "contacts"] == image

        (stage,) = (
            one
            for one in layout.labels
            if one.kind is StageLabelKind.CROSS_REFERENCE
            and one.subject == coil
            and one.slot == "contacts"
        )
        cells = [cell for row in image.split("\n") for cell in row.split(" | ")]
        column = max(text_width(cell, height=profile.text_height) for cell in cells)
        assert stage.box.width == 2 * (column + 2 * profile.marker_padding)
        assert (
            stage.box.height == (1 + len(rows)) * profile.text_height + 3 * profile.marker_padding
        )


def test_tag_and_marking_label_text_matches_what_the_stage_measured() -> None:
    """For every TAG and MARKING label of the golden, the reader's text is the stage's.

    The D7 CROSS_REFERENCE labels are checked by `_check_contact_references`; the D9 star
    markers, all of the golden's markers, are counted here and their text is checked on the
    narrow golden, the one that also has severed cuts.
    """
    model = lay_out_schematic(freeze(build_cabinet()))[0]
    inputs = read_inputs(model)
    drawn, _resolve_findings = resolve(
        inputs.functions, rules=DEFAULT_RULES, choices=inputs.choices
    )
    requests = label_requests(inputs.label_texts, drawn)
    text_of = {
        (request.kind.value, request.subject, request.slot): request.text for request in requests
    }

    labels = layout_of(model, Label)
    markers = layout_of(model, LinkMarker)
    assert len(markers) == _EXPECTED_WIDE_MARKER_COUNT
    assert (
        sum(1 for marker in markers.values() if marker.star is StarKind.REF)
        == _EXPECTED_WIDE_REF_MARKER_COUNT
    )
    stars = {marker.star for marker in markers.values() if marker.key[3] != "line_stub"}
    assert stars == {StarKind.REF, StarKind.BRANCH}, (
        "the wide golden has no cross-page cut: every marker but the line stub is a D9 star"
    )
    (line_stub,) = (marker for marker in markers.values() if marker.key[3] == "line_stub")
    assert line_stub.star is StarKind.OFF

    checked = 0
    cross_references = 0
    for label in labels.values():
        if label.kind is ModelLabelKind.CROSS_REFERENCE:
            cross_references += 1
            continue
        # Exactly one of `function`/`port` is set, by `label.kind`
        # (`write.labels.labels`, the writer this test checks against): the cast trusts that
        # rather than re-checking it.
        subject = cast(
            "Id[Any]",
            {
                ModelLabelKind.TAG: label.function,
                ModelLabelKind.MARKING: label.port,
            }[label.kind],
        )
        expected = text_of[label.kind.value, subject, label.slot]
        assert label_text(model, label) == expected
        checked += 1

    assert checked == _EXPECTED_TAG_MARKING_COUNT
    assert cross_references == _EXPECTED_WIDE_CROSS_REFERENCE_COUNT
    layout, _drawn, _findings = run_stages(model, inputs)
    _check_contact_references(model, inputs, layout)


def _narrow_layout(
    normalized: Callable[[Model], Model],
) -> tuple[Model, StageInputs, Layout, tuple[Any, ...]]:
    """The narrow (158 mm) model, its inputs, its stage `Layout` and the re-run tag echoes.

    `links` is called a second time, over inputs reconstructed from `run_stages`' own public
    output (`layout.placed`, `drawn`, `layout.pages`), rather than the model's persisted
    records: `links` is pure (root CLAUDE.md invariant 1), so this reproduces the exact severed
    `LinkMarker`s the engine wrote (the star markers are added after `links`, by the engine)
    and the tag-echo `CROSS_REFERENCE` `LabelRequest`s, not a fresh re-derivation of the
    text -- the same pattern `resolve`/`label_requests` already use above for
    TAG/MARKING.

    `_narrow_sheet_draft` is a second, independent construction of the sheet `test_usecases
    ._on_sheet` builds; this asserts the rebuilt model's `digests["layout"]` against the
    committed `cabinet_narrow_layout_digest.txt` before either loop trusts it, so the two
    constructions drifting apart fails loudly here instead of silently checking the wrong
    layout against the golden's own claimed counts.
    """
    model = lay_out_schematic(freeze(_narrow_sheet_draft()))[0]
    digest_golden = _NARROW_DIGEST_GOLDEN.read_text(encoding="utf-8")
    # The golden's digest is of the `normalized` model; `model` stays as laid out for the loops.
    assert normalized(model).digests["layout"] + "\n" == digest_golden, (
        "_narrow_sheet_draft has drifted from the committed narrow golden: "
        "these loops would be checking the wrong layout"
    )
    inputs = read_inputs(model)
    layout, drawn, _findings = run_stages(model, inputs)
    location_paths = {
        plan.drawing_set: location_path(model, plan.location)
        for plan in layout.pages
        if plan.location is not None
    }
    units = {plan.drawing_set: plan.unit for plan in layout.pages}
    # The engine draws a D9 star net by its markers and drops its conductors
    # before `cuts` (stages/references/nets.py, `without_starred`, `dropped`):
    # a conductor with a star marker at both ends is a star's. This filter is
    # a second copy of the engine's star drop; one home would need the engine
    # to expose its pruned inputs (noted for the functional-core package).
    # Left in, a star reference that stands on another page than a branch
    # (D7 moved `X2:1` to page 2) makes `cuts` cut it, and the re-run no
    # longer reproduces the engine's own markers.
    star_ports = {marker.port for marker in layout.markers if marker.star}
    connections = tuple(c for c in inputs.connections if not {c.a.port, c.b.port} <= star_ports)
    _decisions, markers, references, _link_findings = built_links(
        connections,
        inputs.net_groups,
        layout.placed,
        drawn,
        sheet=inputs.sheet,
        profile=inputs.profile,
        location_paths=location_paths,
        units=units,
        function_units={spec.function: spec.unit for spec in inputs.functions},
    )
    assert markers == tuple(marker for marker in layout.markers if not marker.star), (
        "links is not pure: the re-run gave different markers"
    )
    return model, inputs, layout, references


def _expected_line_count(stage_marker: StageLinkMarker, profile: StageProfile) -> int:
    """The number of text lines the stage reserved room for, from its own box alone.

    S20 M1, M3: a vertical box is the horizontal one turned, so its lines stand side by side
    across its width, and a horizontal box stacks them down its height; either way the
    thickness is `lines * profile.text_height + 2 * marker_padding`.
    Layout builds no marker text at all (D4): `marker_text` prints every line at
    read time from the persisted records, so there is no literal stage-built text left to
    compare word for word (the D2 equality this module otherwise proves). The stage's own
    line count is still exactly recoverable from its box, so the agreement is checked
    by count instead: a disagreement here means derive printed a different number of lines
    than the box the stage built has room for, a merged stub's extra line included.
    """
    thickness = stage_marker.box.width if stage_marker.vertical else stage_marker.box.height
    return (thickness - 2 * profile.marker_padding) // profile.text_height


def test_marker_text_line_count_matches_the_stage_reserved_box_on_the_narrow_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """For every `layout.link_marker` of the narrow golden, `marker_text`'s line count matches
    the box height the stage reserved for it (D2 equality, mechanical: see
    `_expected_line_count`) -- the one severed cut and the D9 star markers (branch and
    reference), none a per-core off stub in this fixture; `W1`'s line stubs print one line.
    Every reference line of one marker shares one `#<n>-` prefix.
    """
    if regenerate:
        pytest.skip("--regenerate-golden: test_usecases.py rewrites the narrow digest later")
    model, _inputs, layout, _references = _narrow_layout(normalized)
    stage_markers = layout.markers
    assert len({marker.drawing_set for marker in stage_markers}) == 1, (
        "the narrow golden is expected to stay in one drawing set: no marker crosses one"
    )
    assert len([marker for marker in stage_markers if not marker.star]) == (
        _EXPECTED_NARROW_SEVERED_MARKER_COUNT
    )
    stage_marker_of = {(m.page, m.port, m.star): m for m in stage_markers}
    assert len(stage_marker_of) == len(stage_markers), "one marker per page, port and kind"

    pages = layout_of(model, Page)
    profile = DEFAULT_PROFILE
    checked = 0
    line_stubs = 0
    for marker in layout_of(model, LinkMarker).values():
        if marker.key[3] == "line_stub":
            # HL18: no stage marker; one line of text, no reference (C1)
            assert "\n" not in marker_text(model, marker)
            assert not marker_text(model, marker).startswith("#")
            line_stubs += 1
            continue
        key = (pages[marker.page].number, marker.port, marker.star.value if marker.star else "")
        stage_marker = stage_marker_of[key]
        lines = marker_text(model, marker).split("\n")
        expected = _expected_line_count(stage_marker, profile)
        assert len(lines) == expected, (
            f"marker {marker.id}: {len(lines)} lines, box fits {expected}"
        )
        numbers = {line.split("-", 1)[0] for line in lines if line.startswith("#")}
        assert len(numbers) <= 1, f"marker {marker.id}: every reference line shares one #n"
        checked += 1

    assert checked == _EXPECTED_NARROW_MARKER_COUNT
    assert line_stubs == _EXPECTED_NARROW_LINE_STUB_COUNT


def test_cross_reference_label_text_matches_the_stage_request_on_the_narrow_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """For every `CROSS_REFERENCE` label of the narrow golden, the reader's text is the stage's.

    Under D7 these are the contact lines and the contact images, each checked against the
    positions of the coil and its contacts (`_check_contact_references`, the same check the
    wide golden gets). The tag echo of the K8 `LATCH` net group is gone: `links` finds no net
    group cut, so it has no `CROSS_REFERENCE` request to compare (asserted below).
    """
    if regenerate:
        pytest.skip("--regenerate-golden: test_usecases.py rewrites the narrow digest later")
    model, inputs, layout, references = _narrow_layout(normalized)
    assert references == ()
    cross_references = [
        label
        for label in layout_of(model, Label).values()
        if label.kind is ModelLabelKind.CROSS_REFERENCE
    ]
    assert len(cross_references) == _EXPECTED_NARROW_CROSS_REFERENCE_COUNT
    _check_contact_references(model, inputs, layout)
