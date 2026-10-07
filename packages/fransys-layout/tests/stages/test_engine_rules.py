"""The rules the engine used to hold (spec D6, D8): hand-made values, no model.

`without_starred` (stages/star), `with_off_markers` and `black_box_sets` (stages/off_markers) and
`off_ends` (stages/offstubs). Function `n` has ports `n1`... `samples`: port `13` is `hid("port",
n * 10 + 1)`, port `14` is `hid("port", n * 10 + 2)`. Units: `_P` and `_Q` are top-level, `_N` is
nested in `_P`; drawing set 1 is `_P`'s, 2 is `_N`'s, 3 is `_Q`'s.
"""

from dataclasses import replace

import pytest
from samples import (
    PROFILE,
    SHEET,
    built,
    connection,
    drawn,
    function_spec,
    hid,
    page_plan,
    placed,
    stands_of,
)

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.offstubs import OffEnd, PortText, off_ends
from fransys_layout.stages.references import (
    BlackBoxReads,
    OffInputs,
    Star,
    black_box_sets,
    with_off_markers,
    without_starred,
)
from fransys_layout.stages.references.types import MarkerDecision, MarkerScene, Seat, Seating
from fransys_layout.stages.stacking import PageStack
from fransys_layout.stages.types import (
    MarkerSide,
    NetGroup,
    PortRef,
    Role,
    StubText,
)

_P, _Q, _N = hid("unit", 1), hid("unit", 2), hid("unit", 3)


def _star(*ports: int, conductors: tuple[int, ...] = ()) -> Star:
    """A star over the `14` ports of functions `ports`, dropping the conductors `conductors`."""
    refs = tuple(PortRef(function=hid("function", n), port=hid("port", n * 10 + 2)) for n in ports)
    return Star(
        ports=refs,
        ref=refs[0],
        conductors=frozenset(hid("conductor", n) for n in conductors),
        by_designation=False,
    )


def _group(*ports: int) -> NetGroup:
    """A declared net over the `14` ports of functions `ports`."""
    return NetGroup(
        net=hid("net", 500),
        physical_net=hid("net", 500),
        role=Role.CONTROL,
        ports=tuple(
            PortRef(function=hid("function", n), port=hid("port", n * 10 + 2)) for n in ports
        ),
    )


# --- without_starred ------------------------------------------------------------------


def test_the_conductors_a_star_drops_leave_the_connections() -> None:
    # UNDO: stages/star.py `without_starred`: `if c.handle not in dropped` -> `if True`
    kept, dropped = connection(1, 1, 2), connection(2, 1, 3)
    connections, _ = without_starred((kept, dropped), (), (_star(1, 2, 3, conductors=(2,)),))
    assert connections == (kept,)


def test_a_star_ports_leave_a_net_group_and_a_group_left_with_one_port_goes() -> None:
    """A group keeps its wire-drawn ports; with fewer than two left it is dropped whole."""
    # UNDO: stages/star.py `without_starred`: `> 1` -> `> 0` (the one-port group stays)
    # UNDO: stages/star.py `without_starred`: `if r.port not in in_star` -> `if True` (no port
    #   leaves the group)
    _, groups = without_starred((), (_group(4, 5, 6), _group(3, 5)), (_star(3, 6),))
    (only,) = groups
    assert [ref.function for ref in only.ports] == [hid("function", 4), hid("function", 5)]


# --- with_off_markers -----------------------------------------------------------------

_PORT = hid("port", 12)  # port `14` of function 1: one conductor leaves it, to function 90
_TEXT = StubText(cable="-W1", far="+DB-X1", port=":1")


_HOME = placed(1, x=64, y=160)


def _seating() -> Seating:
    """Function 1 seated on page 1 of set 1, column "a": the stub stands at its home."""
    stands, _ = stands_of((_HOME,), (drawn(1),))
    stack = PageStack(
        ports=frozendict({(_HOME.column, port): stand for (port, _), stand in stands.items()}),
        heights=frozendict(),
        last=frozendict(),
        room=0,
    )
    seat = Seat(_HOME.function, _HOME.drawing_set, _HOME.page, _HOME.column)
    return Seating((page_plan(("a",)),), (), (drawn(1),), (seat,), {(1, 1): stack})


def _off(*, texts: tuple[PortText, ...] = (PortText(port=_PORT, text=_TEXT),)) -> OffInputs:
    return OffInputs(SHEET, PROFILE, (connection(1, 1, 90),), texts, {})


def _decision(port, *, star: str) -> MarkerDecision:
    """A text of `star` kind on `port` (of function 1) on page 1 of set 1, naming itself."""
    return MarkerDecision(
        connection=hid("conductor", 1),
        function=hid("function", 1),
        port=port,
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        star=star,
        size=(48, 12),
        partner=port,
        partner_set=1,
        partner_page=1,
    )


def test_an_off_stub_on_a_references_port_comes_back_as_that_reference_one_marker() -> None:
    """D9 (F7): the reference keeps its star kind, holds the stub's text, and is the only text;
    `texts` builds it one line taller."""
    # UNDO: stages/references/off_stubs.py `with_off_markers`: `refs={...}` -> `refs={}` (the
    #   stub is a second text on the port)
    # UNDO: stages/references/off_stubs.py `with_off_markers`: `merged.get((m.port,
    #   m.drawing_set, m.page), m) if m.star == "ref" else m` -> `m` (the reference stays)
    ref = _decision(_PORT, star="ref")
    (merged,) = with_off_markers((ref,), _seating(), _off())
    assert merged.star == "ref"
    assert merged.port == _PORT
    assert merged.merge == _TEXT
    scene = MarkerScene((_HOME,), (drawn(1),), SHEET, PROFILE)
    (grown,), (plain,) = built(scene, (merged,)), built(scene, (ref,))
    assert grown.text.startswith("-W1")
    assert grown.box.height > plain.box.height  # the box grew by the stub's line


def test_an_off_stub_on_no_reference_is_appended_after_the_markers() -> None:
    """A stub that merges nowhere is a text of its own, at the end."""
    # UNDO: stages/references/off_stubs.py `with_off_markers`: `*(m for m in offs if m.star !=
    #   "ref")` -> `*()` (the stub is lost)
    branch = _decision(hid("port", 99), star="branch")
    kept, stub = with_off_markers((branch,), _seating(), _off())
    assert kept == branch
    assert (stub.star, stub.port, stub.end_text) == ("off", _PORT, _TEXT)


# --- black_box_sets -------------------------------------------------------------------

_TOP = {None: None, _P: _P, _Q: _Q, _N: _P}
_SET_UNIT = {1: _P, 2: _N, 3: _Q}


def _reads(*, edges: tuple[int, ...] = ()) -> BlackBoxReads:
    return BlackBoxReads(
        nested=frozenset({_N}),
        edges=frozenset(hid("function", n) for n in edges),
        top=_TOP.__getitem__,
    )


def _sets(placements: list[tuple[int, int]], units: dict[int, object], *, edges=()):
    """`black_box_sets` for `(function, drawing_set)` placements of functions in `units`."""
    specs = [replace(function_spec(n), unit=unit) for n, unit in units.items()]
    return black_box_sets(
        specs,
        tuple(replace(placed(n, x=0, y=0), drawing_set=s) for n, s in placements),
        {spec.function: spec.unit for spec in specs},
        _SET_UNIT,
        _reads(edges=edges),
    )


def test_a_nested_units_function_in_the_parents_set_is_a_black_box_there_only() -> None:
    """Placed in its own unit's set it is no black box; in the parent's set it is."""
    # UNDO: stages/off_markers.py `black_box_sets`: drop `unit_of[one.function] !=
    #   set_unit[one.drawing_set]` (the nested unit's own set counts too)
    # UNDO: stages/off_markers.py `black_box_sets`: `unit_of[one.function] in nested` -> `True`
    #   (a top-level unit's function is in the result)
    found = _sets([(1, 1), (1, 2), (3, 1)], {1: _N, 3: _P})
    assert found == {hid("function", 1): frozenset({1})}


def test_a_pass_through_pin_is_a_black_box_on_the_top_level_units_own_set_only() -> None:
    """A pin that bounds the top-level unit too stubs in `_P`'s set, not in `_Q`'s."""
    # UNDO: stages/off_markers.py `black_box_sets`: `own in (None, set_unit[one.drawing_set])`
    #   -> `own in (None, set_unit[one.drawing_set]) or True` (the pin stubs on `_Q`'s set too)
    # UNDO: stages/off_markers.py `black_box_sets`: `reads.top(spec.unit)` ->
    #   `spec.unit` (the nested unit is taken for the top-level one, the pin never stubs)
    found = _sets([(2, 1), (2, 2), (2, 3)], {2: _N}, edges=(2,))
    assert found == {hid("function", 2): frozenset({1})}


# --- off_ends -------------------------------------------------------------------------


def _end(port, text: StubText = _TEXT, *, far: int = 7) -> OffEnd:
    return OffEnd(port=port, text=text, carrier=hid("item", 5), far=hid("port", far))


def test_a_stand_in_port_copies_its_mates_end_under_its_own_port() -> None:
    """The stand-in's text equals its mate's, so it gets the mate's carrier and far port."""
    # UNDO: stages/offstubs.py `off_ends`: `dataclasses.replace(by_text[one.text], port=one.port)`
    #   -> `by_text[one.text]` (the stand-in keeps its mate's port)
    stand_in = hid("port", 33)
    found = off_ends(
        (_end(_PORT),),
        (PortText(port=_PORT, text=_TEXT), PortText(port=stand_in, text=_TEXT)),
    )
    assert [end.port for end in found] == [_PORT, stand_in]
    assert {(end.carrier, end.far) for end in found} == {(hid("item", 5), hid("port", 7))}


def test_one_text_naming_two_different_far_ends_is_refused() -> None:
    """Two ends of one text with two different far ports: `LayoutError`."""
    # UNDO: stages/offstubs.py `off_ends`: `!= (end.carrier, end.far)` -> `!= (known.carrier,
    #   known.far)` (nothing is refused)
    ends = (_end(_PORT), _end(hid("port", 33), far=8))
    with pytest.raises(LayoutError, match="two different"):
        off_ends(ends, (PortText(port=_PORT, text=_TEXT),))
