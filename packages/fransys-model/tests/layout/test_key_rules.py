"""design/layout-namespace.md, decision 0025: how a derived record's authoring key is built.

The engine that writes these records is not in this package, so these tests hold the rules
against the fixtures and show what each discriminator is for: without it, two records that
must exist would get one id.
"""

import pytest
from layout_examples import DRAWING_SET_KEY, PAGE_KEY, drawing_set, group_node, page

from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.layout import (
    DrawingSet,
    Label,
    LinkMarker,
    Page,
    PageRole,
    RoutePoint,
    SymbolPlacement,
)
from fransys_model.layout.order import by_index

_ENGINE = ("layout", "example-engine")
_FUNCTION = ("examples", "pump1", "contactor", "fn", "main")
_LEFT = ("examples", "function", "pump1")
_RIGHT = ("examples", "function", "pump2")

# Each builder takes the discriminator its rule adds and leaves it out when given nothing: the
# stripped key of a collision proof is the same builder called without it.


def _placement_key(*replica_group: str) -> tuple[str, ...]:
    """A home placement has no discriminator; a replica adds the key of its column's group."""
    return (*_ENGINE, "symbol_placement", *_FUNCTION, *replica_group)


def _label_key(*replica_group: str) -> tuple[str, ...]:
    """The subject's key, the kind value and the slot; a replica adds the same group key."""
    return (*_ENGINE, "label", *_FUNCTION, "tag", "tag", *replica_group)


def _marker_key(port: tuple[str, ...], side: str, partner: tuple[str, ...] = ()) -> tuple[str, ...]:
    return (*_ENGINE, "link_marker", *port, side, *partner)


def _drawing_set_key(location: tuple[str, ...] | None) -> tuple[str, ...]:
    """The location node's key, `unlocated` for none; `()` leaves the location out."""
    return (*_ENGINE, "drawing_set", *(("unlocated",) if location is None else location))


def _page_key(
    drawing_set_key: tuple[str, ...],
    group: tuple[str, ...],
    role: PageRole,
    ordinal: int | None,
) -> tuple[str, ...]:
    """The drawing set's key, the first group's key, the role and the ordinal; `None` omits it."""
    return (*drawing_set_key, *group, role.value, *(() if ordinal is None else (str(ordinal),)))


def _needs_discriminator[R](
    record_type: type[R],
    keys: tuple[tuple[str, ...], tuple[str, ...]],
    stripped: tuple[tuple[str, ...], tuple[str, ...]],
) -> None:
    """The two `keys` are two ids by the rule and one id once the discriminator is `stripped`."""
    assert make_id(record_type, keys[0]) != make_id(record_type, keys[1])
    assert stripped[0] == stripped[1]
    assert make_id(record_type, stripped[0]) == make_id(record_type, stripped[1])


def test_the_fixtures_follow_the_drawing_set_and_page_rules() -> None:
    """A drawing set is engine, kind and location (`unlocated` for none); a page extends it."""
    assert drawing_set().key == DRAWING_SET_KEY == _drawing_set_key(None)
    assert page().key == PAGE_KEY == _page_key(DRAWING_SET_KEY, group_node().key, PageRole.POWER, 0)
    assert PAGE_KEY[: len(DRAWING_SET_KEY)] == DRAWING_SET_KEY


def test_two_locations_are_two_drawing_sets_only_by_the_location_key() -> None:
    """Without the location segment the drawing sets of two locations would share one id."""
    c1, c2 = ("examples", "location", "c1"), ("examples", "location", "c2")
    _needs_discriminator(
        DrawingSet,
        (_drawing_set_key(c1), _drawing_set_key(c2)),
        (_drawing_set_key(()), _drawing_set_key(())),
    )


def test_the_drawing_set_of_no_location_is_told_from_a_located_one_by_unlocated() -> None:
    """`unlocated` stands for no location: it is not the key of any node."""
    located = make_id(DrawingSet, _drawing_set_key(("examples", "location", "c1")))
    assert make_id(DrawingSet, _drawing_set_key(None)) != located
    assert _drawing_set_key(None)[-1] == "unlocated"


def test_a_page_key_holds_no_page_number_so_ids_survive_repagination() -> None:
    """The fixture page is number 1 and its key has no `1`: only the ordinal `0` is there."""
    assert str(page().number) not in PAGE_KEY
    assert PAGE_KEY[-1] == "0"


def test_the_two_pages_of_a_split_group_are_told_apart_by_the_ordinal() -> None:
    """One first group and one role on two pages: without the ordinal they share one id."""
    _needs_discriminator(
        Page,
        (
            _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, 0),
            _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, 1),
        ),
        (
            _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, None),
            _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, None),
        ),
    )


def test_two_groups_of_one_role_are_told_apart_by_the_first_groups_key() -> None:
    """Two pages of one role starting at different groups: without the group key, one id."""
    _needs_discriminator(
        Page,
        (
            _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, 0),
            _page_key(DRAWING_SET_KEY, _RIGHT, PageRole.POWER, 0),
        ),
        (
            _page_key(DRAWING_SET_KEY, (), PageRole.POWER, 0),
            _page_key(DRAWING_SET_KEY, (), PageRole.POWER, 0),
        ),
    )


def test_two_roles_of_one_group_are_told_apart_by_the_role() -> None:
    """The role is in the page key: one group's pages of two roles are two pages."""
    power = _page_key(DRAWING_SET_KEY, _LEFT, PageRole.POWER, 0)
    control = _page_key(DRAWING_SET_KEY, _LEFT, PageRole.CONTROL, 0)
    assert make_id(Page, power) != make_id(Page, control)


def test_two_severed_conductors_on_one_port_get_two_markers() -> None:
    """The partner port key is in the key: without it both owner markers would share an id."""
    port = ("examples", "port", "1")
    _needs_discriminator(
        LinkMarker,
        (
            _marker_key(port, "owner", ("examples", "port", "2")),
            _marker_key(port, "owner", ("examples", "port", "3")),
        ),
        (_marker_key(port, "owner"), _marker_key(port, "owner")),
    )


def test_a_replica_placement_is_told_from_the_home_placement_by_its_group() -> None:
    """A terminal drawn again in another group: without the group key it is the home's id."""
    _needs_discriminator(
        SymbolPlacement,
        (_placement_key(), _placement_key(*_LEFT)),
        (_placement_key(), _placement_key()),
    )


def test_two_replica_placements_are_told_apart_by_their_groups() -> None:
    """Replicas in two groups: without the group key they share one id."""
    _needs_discriminator(
        SymbolPlacement,
        (_placement_key(*_LEFT), _placement_key(*_RIGHT)),
        (_placement_key(), _placement_key()),
    )


def test_a_replica_label_is_told_from_the_home_label_by_the_same_group_key() -> None:
    """A label on a replica placement adds the placement's group key after kind and slot."""
    _needs_discriminator(
        Label,
        (_label_key(), _label_key(*_LEFT)),
        (_label_key(), _label_key()),
    )
    assert _label_key(*_LEFT)[-len(_LEFT) :] == _LEFT
    assert _label_key(*_LEFT)[: -len(_LEFT)] == _label_key()


def test_two_replica_labels_are_told_apart_by_their_groups() -> None:
    """Labels of the terminal's replicas in two groups: without the group key, one id."""
    _needs_discriminator(
        Label,
        (_label_key(*_LEFT), _label_key(*_RIGHT)),
        (_label_key(), _label_key()),
    )


def test_by_index_orders_entries_regardless_of_input_order() -> None:
    """`by_index` returns its entries sorted by `.index`, however they were authored."""
    zero = RoutePoint(index=0, x=0, y=0)
    one = RoutePoint(index=1, x=0, y=0)
    two = RoutePoint(index=2, x=0, y=0)
    ordered = by_index((two, zero, one), RoutePoint, kind="layout.route", holder=None)
    assert ordered == (zero, one, two)


def test_by_index_with_a_shared_index_raises_naming_the_kind_and_the_holder() -> None:
    """Two entries sharing an `index` raise `SchemaError` naming the kind, holder and index."""
    holder = Id(kind="layout.route", value="5" * 32)
    with pytest.raises(SchemaError, match="two entries share the index 0") as excinfo:
        by_index(
            (RoutePoint(index=0, x=0, y=0), RoutePoint(index=0, x=1, y=1)),
            RoutePoint,
            kind="layout.route",
            holder=holder,
        )
    assert excinfo.value.kind == "layout.route"
    assert excinfo.value.record_id == holder
