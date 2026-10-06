"""S21: `references` decides every connection; a wired one whose ends stand apart in another set.

A harness core (conductor 1) joins plug `1`'s port `14` to plug `2`'s port `13` (`samples`: port
`14` of function `n` is `hid("port", n * 10 + 2)`, port `13` is `hid("port", n * 10 + 1)`). Set 1
is the harness's location sheet, where both plugs stand on page 1 and the core is wired; set 2 is
the unit's overview, whose plugs are paged apart unless a test says otherwise.
"""

from samples import PROFILE, SHEET, connection, drawn, hid

from fransys_layout.stages.references.apart import apart_markers
from fransys_layout.stages.references.types import MarkerScene, Seat, Star
from fransys_layout.stages.types import MarkerSide, PortRef

_CORE = connection(1, 1, 2)
_A, _B = hid("port", 12), hid("port", 21)
# a star net the core is a kept wire of: its per-set branches draw the core's ends apart
_STAR = Star(
    ports=(_CORE.a, _CORE.b, PortRef(function=hid("function", 3), port=hid("port", 31))),
    ref=_CORE.a,
    conductors=frozenset(),
    by_designation=False,
    wires=frozenset({_CORE.handle}),
)


def _scene(*seats: tuple[int, int, int]) -> MarkerScene:
    """Function `n` seated on page `page` of `drawing_set` for each `(n, drawing_set, page)`."""
    return MarkerScene(
        tuple(Seat(hid("function", n), s, p, ("invented", f"fn{n}")) for n, s, p in seats),
        (drawn(1), drawn(2)),
        SHEET,
        PROFILE,
    )


_APART = _scene((1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 2))


def _named(
    scene: MarkerScene, exempt: frozenset = frozenset(), stars: tuple[Star, ...] = ()
) -> list[tuple]:
    return [
        (m.port, m.drawing_set, m.page, m.side, m.star, m.lines, m.partner, m.partner_page)
        for m in apart_markers((_CORE,), scene, exempt, stars)
    ]


def test_a_harness_core_whose_plugs_stand_on_two_pages_of_a_set_is_a_reference_pair() -> None:
    """The owner at the plug on the earlier page, the user at the other; each names the other."""
    # UNDO: stages/references/apart.py `_apart`: `if in_a and in_b and not set(in_a) &
    #   set(in_b)` -> `if False` (no pair: the field case's CONNECTION_NOT_DRAWN)
    assert _named(_APART) == [
        (_A, 2, 1, MarkerSide.OWNER, "branch", 1, _B, 2),
        (_B, 2, 2, MarkerSide.USER, "branch", 1, _A, 1),
    ]


def test_the_owner_is_the_end_on_the_earlier_page_whichever_end_it_is() -> None:
    swapped = _scene((1, 1, 1), (2, 1, 1), (1, 2, 3), (2, 2, 2))
    assert [(port, page, side) for port, _, page, side, *_ in _named(swapped)] == [
        (_B, 2, MarkerSide.OWNER),
        (_A, 3, MarkerSide.USER),
    ]


def test_each_set_that_holds_the_plugs_apart_gets_its_own_pair_in_set_order() -> None:
    """Set 3 seats the plugs apart too (on its pages 1 and 3): a second pair, there."""
    scene = _scene((1, 3, 1), (2, 3, 3), (1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 2))
    assert [(port, drawing_set, page) for port, drawing_set, page, *_ in _named(scene)] == [
        (_A, 2, 1),
        (_B, 2, 2),
        (_A, 3, 1),
        (_B, 3, 3),
    ]


def test_plugs_on_one_page_of_every_set_get_no_reference() -> None:
    assert _named(_scene((1, 1, 1), (2, 1, 1), (1, 2, 2), (2, 2, 2))) == []


def test_an_end_exempt_in_the_set_gets_no_reference_there() -> None:
    """A unit's boundary pin that takes no marker in a set (`exempt.boundary_exempt`)."""
    assert _named(_APART, frozenset({(_A, 2)})) == []
    assert _named(_APART, frozenset({(_B, 2)})) == []


def test_a_wire_of_a_star_net_is_left_to_the_stars_branches() -> None:
    """layout-0070: the star already gives each port apart in a set its branch there; a second
    text at that port and page would share the star's marker key."""
    # UNDO: stages/references/apart.py `apart_markers`: `conductor.handle in starred or ` ->
    #   `` (the pump station's PE star: two LinkMarker records share one key)
    assert _named(_APART, stars=(_STAR,)) == []
    assert _named(_APART, stars=(_STAR.__replace__(wires=frozenset()),)) != []


def test_a_core_whose_ends_share_no_page_anywhere_is_left_to_links() -> None:
    """`links` cuts it (design/links.md 6.6); a second text pair here would be a marker too many."""
    assert _named(_scene((1, 2, 1), (2, 2, 2))) == []
