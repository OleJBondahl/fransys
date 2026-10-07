"""A LEAD joins a device's own lead to a pin of a fitted connector (HA5, HA6, model-0172).

It is a link like a mount: it closes its net, is never a wire, and the connector reads through
its parent device (`K1-J1`) while no other child of a device changes.
"""

from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import pytest

from fransys_model.derive import cable_rows, item_designation, net_of, wire_rows
from fransys_model.vocab import ConductorKind, WireFacet
from fransys_model.vocab.tables import conductors, facets_of, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id

_RELAY = "DEMO-RLY-2CO-24"
_PLUG = "DEMO-CONN-2P"


def _designations(result: fr.BuildResult) -> dict[str, str]:
    """Every item's printed designation, by the last part of its authoring key."""
    model = result.model
    return {items(model)[i].key[-1]: item_designation(model, i) for i in items(model)}


def _build() -> fr.BuildResult:
    """Relays K1 and K2, each with a plug J1 on its coil leads; K1 also has a loose plug J2.

    A strip X1 and a plain wire K1 to the strip sit beside them.
    """
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    cab = d.location("CAB", "Cabinet")
    g = d.group("G", "Group")
    relays = [d.item(_RELAY, name=f"k{i}", tag=f"K{i}", at=cab, group=g) for i in (1, 2)]
    for relay in relays:
        plug = d.item(_PLUG, name=f"j1_{relay.key[-1]}", tag="J1", at=cab, group=g, parent=relay)
        d.link(relay["A1"], plug["1"], kind="lead")
        d.link(relay["A2"], plug["2"], kind="lead")
    d.item(_PLUG, name="j2", tag="J2", at=cab, group=g, parent=relays[0])
    strip = d.strip("X1", at=cab)
    t = strip.terminal("DEMO-TB-2.5", "T1", group=g)
    d.wiring(colour="BU", gauge="0.5")(relays[0]["11"], t.outer)
    return fr.build(parts, d.draft())


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    return _build()


def _lead_ends(result: fr.BuildResult) -> list[tuple[Id, Id]]:
    return [(c.a, c.b) for c in conductors(result.model).values() if c.kind is ConductorKind.LEAD]


def test_a_lead_closes_its_net(built: fr.BuildResult) -> None:
    """Can-fail: a net closure that skips LEAD conductors puts the two ends in two nets."""
    ends = _lead_ends(built)
    assert len(ends) == 4
    for a, b in ends:
        assert net_of(built.model, a) == net_of(built.model, b)


def test_a_lead_is_in_no_wire_row_no_cable_row_and_has_no_wire_facet(
    built: fr.BuildResult,
) -> None:
    """Can-fail: wire rows that keep LEAD conductors list four more rows than the one wire."""
    model = built.model
    leads = {c.id for c in conductors(model).values() if c.kind is ConductorKind.LEAD}
    assert leads
    assert not leads & {facet.subject for facet in facets_of(model, WireFacet).values()}
    assert len(wire_rows(model)) == 1
    cables = [i for i in items(model).values() if i.part is None and i.parent is None]
    assert all(cable_rows(model, cable.id) == () for cable in cables)


def test_a_connector_fitted_on_its_parents_leads_reads_through_the_parent(
    built: fr.BuildResult,
) -> None:
    """Can-fail: not widening `designating_ancestors` prints both plugs as `J1`."""
    named = _designations(built)
    assert sorted(v for v in named.values() if v.endswith("J1")) == ["K1-J1", "K2-J1"]
    assert not [f for f in built.findings if f.code == "DESIGNATION_DUPLICATE"]


def test_a_child_of_a_device_with_no_lead_on_it_stays_flat(built: fr.BuildResult) -> None:
    """Can-fail: treating every child of a device as fitted prints `K1-J2`."""
    assert _designations(built)["j2"] == "J2"


def test_a_strip_stays_x1(built: fr.BuildResult) -> None:
    """Can-fail: treating every item beside a fitted one as fitted prints the strip `K1-X1`."""
    strips = [i for i in items(built.model).values() if i.tag == "X1"]
    assert [item_designation(built.model, s.id) for s in strips] == ["X1"]
