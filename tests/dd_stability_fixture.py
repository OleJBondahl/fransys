"""Shared fixture of the F5-C shuffle and stability tests: an example-sized facade cabinet.

Seven groups (six device groups `A`..`F` of a 3-pole contactor, a relay and three terminals
each, and a `PLC` rack with one output module), four pages, three of them shared by two
groups. Wires join relay to relay across groups, so routes are cut and link markers stand on
every page. Imported by `test_dd_shuffle.py` and `test_dd_stability.py` (root `conftest.py`
puts this folder on `sys.path`).
"""

from functools import cache
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

PROJECT: dict[str, Any] = {
    "title": "Stability",
    "number": "P-1003",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}

GROUPS = "ABCDEF"
CROWD = 8
BRANCH_TAG = "KV"  # its coil's port id sorts before the PLC output's: an earlier branch (D9)


def _terminals_on(strip, group, port) -> list:
    """Two terminals of `group` on `strip`, each wired to `port`: the links to author."""
    return [
        (strip.terminal("DEMO-TB-2.5", "T", group=group).inner, port),
        (strip.terminal("DEMO-TB-2.5", "T", group=group).inner, port),
    ]


def build(
    *,
    extra: str | None = None,
    reverse: bool = False,
    crowd: str | None = None,
    branch: str | None = None,
    terminal: str | None = None,
) -> Model:
    """The model of `build_result`, with the same options."""
    return build_result(
        extra=extra, reverse=reverse, crowd=crowd, branch=branch, terminal=terminal
    ).model


@cache
def build_result(
    *,
    extra: str | None = None,
    reverse: bool = False,
    crowd: str | None = None,
    branch: str | None = None,
    terminal: str | None = None,
) -> fr.BuildResult:
    """The cabinet; `extra` adds one relay `KX` to that group; `reverse` authors it backwards.

    `crowd` adds `CROWD` relays `KY1`.. to that group, so the group overflows onto a second page
    and every later page is numbered one higher (B1). `branch` adds one relay `KV` to that group,
    its coil wired to `KA`'s coil `A1`: the star net of `KA.A1`, the terminal `XA` and the PLC
    output gains a branch in another group. `terminal` adds two terminals to that group, wired to
    the PLC output of the same net: the net then has three terminal points and the PLC output has
    the most wires, so its reference moves from the terminal `XA` to the PLC output, which was a
    branch (D9, `stages.references.nets.star_nets`).
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    order = GROUPS[::-1] if reverse else GROUPS
    group = {name: d.group(name, f"Group {name}") for name in order}
    plc_group = d.group("PLC", "PLC")
    strip = d.strip("X1", at=c1)
    q, k, t = {}, {}, {}
    for name in order:
        q[name] = d.item("DEMO-CTR-3P-24", tag=f"Q{name}", at=c1, group=group[name])
        k[name] = d.item("DEMO-RLY-2CO-24", tag=f"K{name}", at=c1, group=group[name])
        t[name] = [strip.terminal("DEMO-TB-2.5", name, group=group[name]) for _ in range(3)]
    rack = d.item(None, tag="U1", at=c1, group=plc_group)
    do = d.item(
        "DEMO-PLC-DO-2", tag="DO1", name="do", parent=rack, position=1, at=c1, group=plc_group
    )
    wire = d.wiring(colour="BU", gauge="0.5")
    links = []
    for i, name in enumerate(GROUPS):
        coil, main, relay = q[name].fn("coil"), q[name].fn("main"), k[name].fn("co_1")
        links += [
            (t[name][0].inner, coil["A1"]),
            (main["2"], t[name][1].inner),
            (t[name][2].inner, k[name].fn("coil")["A1"]),
            (relay["14"], coil["A2"]),
        ]
        if i + 1 < len(GROUPS):
            links.append((k[name].fn("co_2")["24"], k[GROUPS[i + 1]].fn("coil")["A2"]))
        else:  # layout-0112: an unwired contact is not drawn
            links.append((k[name].fn("co_2")["24"], t[name][1].inner))
            links.append((q[name].fn("aux")["14"], t[name][1].inner))
    links.append((do.fn("do_1")["1"], k["A"].fn("coil")["A1"]))
    if extra is not None:
        kx = d.item("DEMO-RLY-2CO-24", tag="KX", at=c1, group=group[extra])
        links += [
            (t[extra][2].inner, kx.fn("coil")["A1"]),
            (kx.fn("co_1")["14"], q[extra].fn("coil")["A2"]),
        ]
    if branch is not None:
        kw = d.item("DEMO-RLY-2CO-24", tag=BRANCH_TAG, at=c1, group=group[branch])
        links.append((kw.fn("coil")["A1"], k["A"].fn("coil")["A1"]))
    if terminal is not None:
        links += _terminals_on(strip, group[terminal], do.fn("do_1")["1"])
    if crowd is not None:
        for n in range(CROWD):
            ky = d.item("DEMO-RLY-2CO-24", tag=f"KY{n + 1}", at=c1, group=group[crowd])
            links.append((t[crowd][2].inner, ky.fn("coil")["A1"]))
    for a, b in links[::-1] if reverse else links:
        wire(a, b)
    return fr.build(parts, d.draft(), layout_trigger_document())


def group_names(model: Model) -> dict:
    return {id_: node.key[-1] for id_, node in model.tables["aspect_node"].items()}


def pages_of(model: Model) -> list[tuple[str, ...]]:
    names = group_names(model)
    pages = sorted(layout_of(model, Page).values(), key=lambda page: page.number)
    return [tuple(names[g.group] for g in page.groups) for page in pages]
