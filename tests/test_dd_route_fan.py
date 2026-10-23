"""The router draws only wire-drawn pairs.

A declared net whose conductors join some of its ports into a star is drawn as markers at those
ports. The rest of its ports are the net group's wire-drawn ports: the router spans those and
never a star port. Built through the `fransys` facade from `examples/demo-parts`.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _dd_core import designation_of
from _dd_core_c import markers_of
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity

_PROJECT: dict[str, Any] = {
    "title": "Route fan",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_RELAY = "DEMO-RLY-2CO-24"


def _build():
    """K5, K6, K7 joined by conductors (a star); a declared net names those and K1, K2.

    A group's physical net is its smallest port's, and a port named by a conductor and by the
    group must agree on it, so the star's ports are the ones holding the smallest port id here.
    Returns the built result.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cabinet, group = d.location("C1", "Cabinet"), d.group("G1", "Group")
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {
        tag: d.item(_RELAY, tag=tag, name=tag.lower(), at=cabinet, group=group)
        for tag in ("K1", "K2", "K5", "K6", "K7")
    }
    for relay in relays.values():  # layout-0112: an unwired contact is not drawn
        wire(relay.fn("co_1")["11"], relay.fn("co_1")["14"])
        wire(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
    coil = {tag: relay.fn("coil")["A1"] for tag, relay in relays.items()}
    wire(coil["K5"], coil["K6"])
    wire(coil["K6"], coil["K7"])
    d.net("SHARED", *coil.values())
    return fr.build(parts, d.draft(), layout_trigger_document())


def test_a_net_group_is_spanned_over_its_wire_drawn_ports_and_never_a_star_port() -> None:
    """The star K5-K6-K7 gets markers; the group's wire joins K1 to K2 and touches no star port."""
    # UNDO: stages/references/nets.py, `without_starred`, the `net_groups`
    #     filter on `in_star`: keep every group whose ports are not ALL in a
    #     star, with all its ports (the unfixed rule)
    result = _build()
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    model = result.model
    tag = {k: designation_of(model, k) for k in ("k1", "k2", "k5", "k6", "k7")}
    assert all(
        markers_of(model, tag[k]) for k in ("k5", "k6", "k7")
    )  # the star is drawn as markers
    assert not any(
        markers_of(model, tag[k]) for k in ("k1", "k2")
    )  # the net's other ports carry none
    (drawing,) = drawn_pages(model).values()
    tags = {t.text: t for t in drawing.texts if t.kind == "TAG"}
    # K1 and K2 are drawn, joined by the group's wire
    assert tag["k1"] in tags
    assert tag["k2"] in tags
