"""`Scope.unit(..., title=, number=)` writes the unit's own identity (UNIT-ID I1)."""

from fransys_author import Design

from fransys_model.vocab import UnitRelease


def _release(design: Design) -> UnitRelease:
    (release,) = [r for r in design.draft().records() if isinstance(r, UnitRelease)]
    return release


def test_title_and_number_land_on_the_unit_release_record(parts):
    d = Design(parts)
    d.scope("u1").unit("x", revision=1, interface="1", title="T", number="N")
    release = _release(d)
    assert (release.title, release.number) == ("T", "N")


def test_a_unit_without_them_has_empty_title_and_number(parts):
    d = Design(parts)
    d.scope("u1").unit("x", revision=1, interface="1")
    release = _release(d)
    assert (release.title, release.number) == ("", "")
