"""PNG READ 2's checks (d) and (e) (designer, 2026-09-27) on the changeover field case's page.

The fixture is the field case `field_cases/test_changeover_throws_to_two_strips.py` inside its
unit, the page the designer read (its PDF's page 2, after the cover). Before S18 two slot labels
there had no free candidate among those `reserve_slots` offered (its moves stayed inside the
owner's keep-out, then the mirror side), and each stood where it was going to anyway:

- (d) the row-1 terminal under throw 32 (strip X02's RUN3) printed its strip tag and its point
  text on top of each other, left of the throw: throw 34's wire blocked the right side, and the
  strip tag fell back to its slot, over the point text (`LABEL_UNPLACED`);
- (e) the first contact's position text `p1:3A`, a cross-reference placed after the page shift
  (C22b shifts first-call labels only), crossed the content box's left edge onto row letter A.

S18 (step 5 ADDENDUM 7) places both through D3's placer (`texts.place_texts`): a candidate is
bounded by the table's steps, never by the keep-out, so the strip tag takes a free step below
its home (d); and the cross-reference call admits a candidate only inside the content box
(`Space.holds`), so `p1:3A` stands on its first free candidate inside it (e).
"""

import importlib.util
from decimal import Decimal
from itertools import combinations
from pathlib import Path

import pytest

from fransys_model.layout import Label, LabelKind, default_sheet_format, layout_of
from fransys_model.vocab.tables import functions

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`, and
# ty cannot resolve a `sys.path` insert; the field case's own build is loaded from its file.
_FIELD_CASE = (
    Path(__file__).resolve().parent / "field_cases" / "test_changeover_throws_to_two_strips.py"
)
_spec = importlib.util.spec_from_file_location("_changeover_field_case_texts", _FIELD_CASE)
assert _spec is not None
assert _spec.loader is not None
_field_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_field_case)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    """The field case's build inside its unit, shared by the module's tests."""
    return _field_case._build(tmp_path_factory.mktemp("texts"), in_unit=True).model


def _interiors_meet(a: Label, b: Label) -> bool:
    return (
        a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.height
        and b.y < a.y + a.height
    )


def test_the_row_one_terminals_strip_tag_and_point_text_do_not_overlap(model) -> None:
    """(d): the terminal under throw 32 prints its two tags apart."""
    # UNDO: stages/texts/place_texts.py: a step past a side's first admitted only within the
    #     label's own keep-out along the side: the strip tag stands at its home, over the point
    fns = functions(model)
    key = ("UNIT", "X02", "terminal", "RUN3", "1", "fn", "terminal")
    tags = [
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.TAG and one.function is not None and fns[one.function].key == key
    ]
    assert len(tags) == 2  # the strip tag and the point text
    assert not any(_interiors_meet(a, b) for a, b in combinations(tags, 2))


def test_every_cross_reference_stays_inside_the_content_box(model) -> None:
    """(e): no contact's position text crosses the frame, `p1:3A` of the first contact included."""
    # UNDO: stages/space.py `Space.holds` returns True: `p1:3A` stands at x -5 again
    sheet = default_sheet_format()
    width = round(sheet.content_width_mm * 8 / Decimal(sheet.module_mm))
    height = round(sheet.content_height_mm * 8 / Decimal(sheet.module_mm))
    references = [
        one for one in layout_of(model, Label).values() if one.kind is LabelKind.CROSS_REFERENCE
    ]
    assert references
    outside = [
        one
        for one in references
        if one.x < 0 or one.y < 0 or one.x + one.width > width or one.y + one.height > height
    ]
    assert outside == []
