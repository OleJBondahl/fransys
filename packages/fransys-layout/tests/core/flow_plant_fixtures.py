"""The S3 plants: a three-level tree and a fan-in with a three-pole cable box."""

from __future__ import annotations

from turn_fixtures import views_of

from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import Box, BoxSpec, Net, Pin, PlacementProblem, Size

from .flow_builders import net, problem

LABEL = Size(16, 8)


def _part(
    sym_id: str,
    body: Box,
    pins: tuple[Pin, ...],
    nodes: tuple[tuple[str, ...], ...] | None = None,
    box: BoxSpec | None = None,
) -> Sym:
    """A symbol at R0 whose nodes are one per pin unless the caller groups them."""
    node_groups = nodes or tuple((p.id,) for p in pins)
    return Sym(
        sym_id,
        None,
        "",
        LABEL,
        pins,
        node_groups,
        views=views_of(body, body, body, pins, ("R0",)),
        box=box,
    )


def tree3() -> PlacementProblem:
    """Hub H with four S pins, children C1 and C2 (one node, two S pins each), leaves G1 to G4."""
    hub_pins = tuple(Pin(f"s{i}", "S", 16 * i, 32, i - 1) for i in range(1, 5))
    hub_spec = BoxSpec(tuple(p.id for p in hub_pins), "S", 16, 16)
    hub = _part("H", Box(0, 0, 80, 32), hub_pins, box=hub_spec)
    children = [
        _part(
            name,
            Box(-16, 0, 32, 32),
            (Pin("n", "N", 0, 0, 0), Pin("s1", "S", -8, 32, 1), Pin("s2", "S", 8, 32, 2)),
            nodes=(("n", "s1", "s2"),),
        )
        for name in ("C1", "C2")
    ]
    leaves = [_part(f"G{i}", Box(-8, 0, 16, 32), (Pin("n", "N", 0, 0, 0),)) for i in range(1, 5)]
    nets: list[Net] = [
        net("H.s1-C1.n", "H.s1", "C1.n"),
        net("H.s2-C2.n", "H.s2", "C2.n"),
        net("C1.s1-G1.n", "C1.s1", "G1.n"),
        net("C1.s2-G2.n", "C1.s2", "G2.n"),
        net("C2.s1-G3.n", "C2.s1", "G3.n"),
        net("C2.s2-G4.n", "C2.s2", "G4.n"),
    ]
    return problem([hub, *children, *leaves], nets)


def _box_and_foot() -> tuple[Sym, Sym, list[Net]]:
    """A 3-pole cable box K (pole dx 0, 16, 32) and bottom end B1 (pins at dx 0, 10, 20)."""
    cable_pins = tuple(
        pin
        for k in range(3)
        for pin in (Pin(f"N{k + 1}", "N", 16 * k, 0, k), Pin(f"S{k + 1}", "S", 16 * k, 32, k))
    )
    cable = _part(
        "K",
        Box(-8, 0, 48, 32),
        cable_pins,
        nodes=tuple((f"N{k + 1}", f"S{k + 1}") for k in range(3)),
    )
    b1 = _part(
        "B1",
        Box(-8, 0, 48, 32),
        tuple(Pin(str(k + 1), "N", 10 * k, 0, k) for k in range(3)),
    )
    nets = [net(f"K.S{k}-B1.{k}", f"K.S{k}", f"B1.{k}") for k in (1, 2, 3)]
    return cable, b1, nets


def fan_in3() -> PlacementProblem:
    """Top ends T1 (2 pins) and T2 (1 pin) into the box K, then B1.

    No end pin dx (T1 0 and 10, T2 4, B1 0, 10, 20) equals the box's pole dx 0, 16, 32.
    """
    t1 = _part("T1", Box(-8, 0, 32, 32), (Pin("1", "S", 0, 32, 0), Pin("2", "S", 10, 32, 1)))
    t2 = _part("T2", Box(-8, 0, 16, 32), (Pin("1", "S", 4, 32, 0),))
    cable, b1, foot = _box_and_foot()
    nets = [
        net("T1.1-K.N1", "T1.1", "K.N1"),
        net("T1.2-K.N2", "T1.2", "K.N2"),
        net("T2.1-K.N3", "T2.1", "K.N3"),
        *foot,
    ]
    return problem([t1, t2, cable, b1], nets)


def fan_in1() -> PlacementProblem:
    """One top end T1, three pins at dx 0, 10, 20, into the box K, then B1."""
    pins = tuple(Pin(str(k + 1), "S", 10 * k, 32, k) for k in range(3))
    t1 = _part("T1", Box(-8, 0, 48, 32), pins)
    cable, b1, foot = _box_and_foot()
    nets = [net(f"T1.{k}-K.N{k}", f"T1.{k}", f"K.N{k}") for k in (1, 2, 3)]
    return problem([t1, cable, b1], [*nets, *foot])


def tree2() -> PlacementProblem:
    """Hub H with two S pins, children C1 and C2, one leaf each."""
    hub_pins = tuple(Pin(f"s{i}", "S", 16 * i, 32, i - 1) for i in (1, 2))
    hub = _part("H", Box(0, 0, 48, 32), hub_pins, box=BoxSpec(("s1", "s2"), "S", 16, 16))
    kids = [
        _part(n, Box(-8, 0, 16, 32), (Pin("n", "N", 0, 0, 0), Pin("s", "S", 0, 32, 1)))
        for n in ("C1", "C2")
    ]
    leaves = [_part(f"G{i}", Box(-8, 0, 16, 32), (Pin("n", "N", 0, 0, 0),)) for i in (1, 2)]
    nets = [
        net("H.s1-C1.n", "H.s1", "C1.n"),
        net("H.s2-C2.n", "H.s2", "C2.n"),
        net("C1.s-G1.n", "C1.s", "G1.n"),
        net("C2.s-G2.n", "C2.s", "G2.n"),
    ]
    return problem([hub, *kids, *leaves], nets)
