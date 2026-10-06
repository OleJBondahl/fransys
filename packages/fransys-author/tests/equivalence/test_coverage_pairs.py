"""EA11, EA12: each spelling of the coverage order, in the engine and the surface, one model."""

from decimal import Decimal
from typing import TYPE_CHECKING

import fransys_parts
from fransys_author import Design
from fransys_author.surface import design

from fransys_model.vocab import FunctionKind, NetClass

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
    "module_mm": Decimal("2.5"),
}
_RLY = "TEST-RLY-2CO"


def _engine_relays(e: Design) -> tuple:
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
        e.keep_together(a, b)
        e.break_before(b)
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        a, b, *_ = _surface_relays(d)
        d.layout.order(a, b)
        d.layout.keep_together(a, b)
        d.layout.break_before(b)
        return d.draft()

    same_model(library, engine, surface)


def test_symbol_chain_and_draw_in_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        _, b, k1, k2 = _engine_relays(e)
        e.symbol(FunctionKind.COIL, "coil_sym")
        e.symbol(k2, "relay_sym")
        e.chain(k1.fn("coil"), k2.fn("coil"))
        e.draw_in(k1.fn("coil"), b)
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        _, b, k1, k2 = _surface_relays(d)
        d.layout.symbol(FunctionKind.COIL, "coil_sym")
        d.layout.symbol(k2, "relay_sym")
        d.layout.chain(k1.coil, k2.coil)
        d.layout.draw_in(k1.coil, b)
        return d.draft()

    same_model(library, engine, surface)


def test_sheet_and_profile_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        e.profile(sheet=e.sheet("A3", **_SHEET))
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        d.layout.profile(sheet=d.layout.sheet("A3", **_SHEET))
        return d.draft()

    same_model(library, engine, surface)


def test_earth_net_busbar_and_rail_bond_pair(library: Draft, same_model) -> None:
    def engine(lib: Draft) -> Draft:
        e = Design(lib)
        k1 = e.item(_RLY, name="K1", tag="K1")
        k2 = e.item(_RLY, name="K2", tag="K2")
        x1 = e.strip("X1")
        e.net("PE", x1.terminal("TEST-TB", index=1).inner, k1.fn("coil")["A2"], cls="pe")
        e.net("SIG", k1.fn("coil")["A1"], k2.fn("coil")["A1"], cls="signal")
        e.link(k1.fn("coil")["A1"], k2.fn("coil")["A1"], kind="bus")
        e.link(k1.fn("coil")["A2"], k2.fn("coil")["A2"], kind="rail")
        return e.draft()

    def surface(lib: Draft) -> Draft:
        d = design(lib)
        k1 = d.device("K1", _RLY)
        k2 = d.device("K2", _RLY)
        x1 = d.terminal_strip("X1", "TEST-TB")
        d.earth(x1[1], k1.coil.A2)
        d.net("SIG", k1.coil.A1, k2.coil.A1, kind=NetClass.SIGNAL)
        d.busbar(k1.coil.A1, k2.coil.A1)
        d.rail_bond(k1.coil.A2, k2.coil.A2)
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


_RATED = (
    'schema = 1\n\n[part]\nmpn = "RT-1"\nmanufacturer = "Demo"\ndescription = "d"\n'
    'category = "generic"\nclass_code = "X"\n\n[rating]\nvoltage_ac_v = "500"\n\n'
    '[[function]]\nname = "coil"\nkind = "generic"\nports = [{ name = "A", role = "generic" }]\n'
    '\n[function.operating]\nnominal_voltage_v = "24"\n'
)


def test_rating_and_operating_pair_compare_values(tmp_path) -> None:
    (tmp_path / "parts").mkdir()
    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts" / "rt1.toml").write_text(_RATED)
    d = design(fransys_parts.load_path(tmp_path))
    e = Design(fransys_parts.load_path(tmp_path))
    assert d.rating("RT-1") == e.rating("RT-1")
    assert d.operating("RT-1", "coil") == e.operating("RT-1", "coil")
    assert d.rating("RT-1") is not None
    assert d.operating("RT-1", "coil") is not None
