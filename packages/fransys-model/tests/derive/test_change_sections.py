"""`change_sections` orders the diff's sections, drops `unit` and groups rows by subject."""

from fransys_model.derive.baseline import Change, ListingDiff, change_sections
from fransys_model.derive.rows_baseline import BaselineUnit

_UNIT = BaselineUnit(name="u", version=1, revision=1, interface="1")


def _row(section: str, subject: str, field: str = "") -> Change:
    return Change(
        section=section,
        change="changed",
        subject=subject,
        field=field,
        before="a",
        after="b",
        parts=(subject,),
        detail="",
    )


def _diff(*rows: Change) -> ListingDiff:
    return ListingDiff(a=_UNIT, b=_UNIT, changes=rows)


def test_sections_come_in_the_printed_order_whatever_the_row_order():
    rows = [_row(name, "s") for name in ("nets", "mates", "conductors", "boundary", "units")]
    rows.append(_row("items", "s"))
    names = [part.section for part in change_sections(_diff(*rows))]
    assert names == ["items", "units", "boundary", "conductors", "mates", "nets"]


def test_the_unit_section_is_never_printed():
    assert change_sections(_diff(_row("unit", "u", "interface"))) == ()


def test_no_change_gives_no_section():
    assert change_sections(_diff()) == ()


def test_consecutive_rows_of_one_subject_are_one_group():
    rows = (_row("items", "a", "x"), _row("items", "a", "y"), _row("items", "b", "x"))
    (part,) = change_sections(_diff(*rows))
    assert [[row.field for row in group] for group in part.groups] == [["x", "y"], ["x"]]
