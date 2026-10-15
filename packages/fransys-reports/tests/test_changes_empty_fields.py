"""`changes_markdown` leaves an empty field out and reads a field set from empty (reports-0006)."""

import dataclasses

from fransys_reports import changes_markdown

from fransys_model.derive.baseline import diff
from fransys_model.derive.rows_baseline import BaselineItem, BaselineUnit, Listing


def _listing(*items: BaselineItem) -> Listing:
    return Listing(
        unit=BaselineUnit(name="u", version=1, revision=1, interface="1"),
        items=items,
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )


def _item(mpn: str = "", manufacturer: str = "") -> BaselineItem:
    return BaselineItem(
        designation="-CU2R",
        mpn=mpn,
        manufacturer=manufacturer,
        installed=True,
        external=False,
        position=None,
    )


def test_a_removed_item_with_no_mpn_and_no_manufacturer_prints_no_empty_detail():
    md = changes_markdown(diff(_listing(_item()), _listing()))
    assert "- Removed `-CU2R`." in md


def test_a_removed_item_with_one_field_set_prints_only_that_field():
    md = changes_markdown(diff(_listing(_item(mpn="M1")), _listing()))
    assert "- Removed `-CU2R`: M1." in md


def test_a_field_set_from_empty_reads_set_to():
    before = _listing(_item())
    after = _listing(dataclasses.replace(_item(), manufacturer="Acme"))
    md = changes_markdown(diff(before, after))
    assert "manufacturer set to Acme" in md
