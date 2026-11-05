"""Each spelling of the coverage order, in the engine and the surface, one model."""

from typing import TYPE_CHECKING, Any

from fransys_author.design import Design
from fransys_author.surface import design

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

_RLY = "TEST-RLY-2CO"


def _engine_relays(e: Design) -> tuple[Any, ...]:
    a, b = e.group("A", "First"), e.group("B", "Second")
    k1 = e.item(_RLY, name="A/K1", tag="K1", group=a)
    k2 = e.item(_RLY, name="B/K2", tag="K2", group=b)
    return a, b, k1, k2


def _surface_relays(d):
    with d.function("A", "First") as a:
        k1 = d.device("K1", _RLY)
    with d.function("B", "Second") as b:
        k2 = d.device("K2", _RLY)
    return a, b, k1, k2


def test_order_hint_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        a, b, *_ = _engine_relays(e)
        e.order(a, b)
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        a, b, *_ = _surface_relays(d)
        d.layout.order(a, b)
        return d.draft()

    same_model(library, engine, surface)


def test_profile_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        e.profile(hide_unused_pins=True)
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        d.layout.profile(hide_unused_pins=True)
        return d.draft()

    same_model(library, engine, surface)


def test_earth_net_and_busbar_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        k1 = e.item(_RLY, name="K1", tag="K1")
        k2 = e.item(_RLY, name="K2", tag="K2")
        x1 = e.strip("X1")
        e.net("PE", x1.terminal("TEST-TB", index=1).inner, k1.fn("coil")["A2"], cls="pe")
        e.link(k1.fn("coil")["A1"], k2.fn("coil")["A1"], kind="bus")
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        k1 = d.device("K1", _RLY)
        k2 = d.device("K2", _RLY)
        x1 = d.terminal_strip("X1", "TEST-TB")
        d.earth(x1[1], k1.coil.A2)
        d.detail.busbar(k1.coil.A1, k2.coil.A1)
        return d.draft()

    same_model(library, engine, surface)


def test_mate_harness_project_and_revision_pair(library: Draft, same_model) -> None:

    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        c1 = e.item("TEST-CONN-2P", name="X2", tag="X2")
        c2 = e.item("TEST-CONN-2P", name="X3", tag="X3")
        e.mate(c1, c2)
        e.harness(name="W5", tag="W5")
        e.project(title="T", number="N", customer="C", revision=1, author="A")
        e.revision(1, date="2026-10-02", text="first", created="A")
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        c1 = d.device("X2", "TEST-CONN-2P")
        c2 = d.device("X3", "TEST-CONN-2P")
        d.mate(c1, c2)
        d.harness("W5")
        d.project(title="T", number="N", customer="C", revision=1, author="A")
        d.revision(1, date="2026-10-02", text="first", created="A")
        return d.draft()

    same_model(library, engine, surface)
