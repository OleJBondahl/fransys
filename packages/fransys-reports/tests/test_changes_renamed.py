"""A `renamed` row prints as "Renamed `old` -> `new`" first in its section (reports-0008)."""

import dataclasses

from fransys_reports import changes_csv, changes_markdown

from fransys_model.derive.baseline import diff
from fransys_model.derive.rows_baseline import BaselineItem, BaselineUnit, Listing

ARROW = "→"


def _item(designation, key, mpn="P1"):
    return BaselineItem(
        designation=designation,
        mpn=mpn,
        manufacturer="",
        installed=True,
        external=False,
        position=None,
        key=key,
    )


def _listing(*items):
    return Listing(
        unit=BaselineUnit(name="u", version=1, revision=1, interface="1"),
        items=tuple(items),
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )


def _renamed_diff():
    before = _listing(_item("-A3", "a3"), _item("-B1", "b1"))
    after = _listing(_item("=CSN-A3", "a3", mpn="P2"), _item("-B1", "b1", mpn="P9"))
    return diff(before, after)


def test_the_note_prints_the_rename_with_both_designations_before_the_real_changes():
    md = changes_markdown(_renamed_diff())
    lines = [line for line in md.splitlines() if line.startswith("- ")]
    assert lines[0] == f"- Renamed `-A3` {ARROW} `=CSN-A3`."
    assert "- Changed `=CSN-A3`: mpn P1 → P2." in lines
    assert "- Changed `-B1`: mpn P1 → P9." in lines


def test_the_csv_writes_renamed_in_the_change_column_first():
    rows = changes_csv(_renamed_diff()).splitlines()
    assert rows[1] == "items,renamed,=CSN-A3,,-A3,=CSN-A3"


def test_a_rename_with_no_other_change_is_one_bullet_and_nothing_else():
    before = _listing(_item("-A3", "a3"))
    after = dataclasses.replace(before, items=(_item("=CSN-A3", "a3"),))
    md = changes_markdown(diff(before, after))
    assert [line for line in md.splitlines() if line.startswith("- ")] == [
        f"- Renamed `-A3` {ARROW} `=CSN-A3`."
    ]


def test_the_renamed_line_and_the_interface_line_both_carry_the_arrow():
    before = _listing(_item("-A3", "a3"))
    after_unit = dataclasses.replace(before.unit, interface="2")
    after = dataclasses.replace(before, unit=after_unit, items=(_item("=CSN-A3", "a3"),))
    md = changes_markdown(diff(before, after))
    assert f"- Renamed `-A3` {ARROW} `=CSN-A3`." in md
    assert f"Interface 1 {ARROW} 2." in md
