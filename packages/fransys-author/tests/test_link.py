"""`Scope.link(a, b, kind=...)` (author-0012): one non-wire conductor of the kind named."""

import pytest
from fransys_author import AuthorError, Design

from fransys_model.kernel import Draft, Record
from fransys_model.vocab import Conductor, ConductorKind, WireFacet


def _only[R: Record](draft: Draft, cls: type[R]) -> tuple[R, ...]:
    return tuple(r for r in draft.records() if isinstance(r, cls))


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("mount", ConductorKind.MOUNT), ("bus", ConductorKind.BUSBAR), ("rail", ConductorKind.RAIL)],
)
def test_link_writes_one_conductor_of_its_kind_with_no_wire_facet(parts, kind, expected):
    """Can-fail: mapping `bus` to `ConductorKind.RAIL` fails the kind assert on `bus`."""
    d = Design(parts)
    strip = d.strip("X1")
    t1, t2 = strip.terminal("TEST-TB", "A"), strip.terminal("TEST-TB", "B")
    d.link(t1.inner, t2.inner, kind=kind)
    (conductor,) = _only(d.draft(), Conductor)
    assert conductor.kind is expected
    assert conductor.carrier is None
    assert {conductor.a, conductor.b} == {t1.inner.id, t2.inner.id}
    assert _only(d.draft(), WireFacet) == ()


def test_link_key_sits_under_the_scope_prefix_and_ignores_end_order(parts):
    d = Design(parts)
    scope = d.scope("p1")
    strip = scope.strip("X1")
    t1, t2 = strip.terminal("TEST-TB", "A"), strip.terminal("TEST-TB", "B")
    scope.link(t1.inner, t2.inner, kind="rail")
    scope.link(t2.inner, t1.inner, kind="rail")
    (conductor,) = _only(d.draft(), Conductor)
    assert conductor.key[0] == "p1"


def test_link_refuses_an_unknown_kind_listing_the_valid_ones(parts):
    d = Design(parts)
    strip = d.strip("X1")
    t1, t2 = strip.terminal("TEST-TB", "A"), strip.terminal("TEST-TB", "B")
    with pytest.raises(AuthorError, match="valid: mount, bus, rail"):
        d.link(t1.inner, t2.inner, kind="wire")


def test_link_refuses_one_port_at_both_ends(parts):
    d = Design(parts)
    t1 = d.strip("X1").terminal("TEST-TB", "A")
    with pytest.raises(AuthorError, match="two different ports"):
        d.link(t1.inner, t1.inner, kind="mount")
