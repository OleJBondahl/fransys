"""A core page with no group is titled by its designations, as today's engine titles it (FIX3 5).

The lamps page (two coils, one wire) printed "-K1, -K2" before the core path and a blank title
after it: the core writes its designations as drawn texts, not labels. A page with a group keeps
"""

import fransys as fr
from _card_case import card_case_drafts, lamps_drafts
from _drawn_pages import drawn_pages

from fransys_model.derive import page_title
from fransys_model.kernel import evolve
from fransys_model.layout import Membership, Page, layout_of


def _written(drafts):
    return fr.build(*drafts).model


def _titles(drafts) -> list[str]:
    written = _written(drafts)
    core = set(drawn_pages(written))
    return [page_title(written, page) for page in layout_of(written, Page).values() if page.id in core]


def test_the_lamps_page_is_titled_by_its_two_designations() -> None:
    assert _titles(lamps_drafts()) == ["-K1, -K2"]


def test_a_page_with_a_group_keeps_the_groups_text() -> None:
    assert "Relays, Card" in _titles(card_case_drafts(16))


def test_the_title_reads_the_membership_rows_not_the_drawings() -> None:
    """Can fail: the membership rows go, and the designations go."""
    written = _written(lamps_drafts())
    stripped = evolve(written, remove=list(layout_of(written, Membership)))
    titles = [page_title(stripped, page) for page in layout_of(stripped, Page).values()]
    assert "-K1, -K2" not in titles
