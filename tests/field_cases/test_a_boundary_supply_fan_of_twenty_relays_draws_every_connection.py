"""Field case: a unit whose 24 V rail enters through an interface strip and a fuse, fanned to twenty relay groups, with a source unit beside it.
The bug (KI-757, consumer set 8): a coil return gets CONNECTION_NOT_DRAWN, MARKER_UNPLACED and DANGLING_WIRE_END, with no PAGE_OVERFLOW.
Fixed at the root: a single-lane copy at a trunk end is a cut end, so the cut and the placement reserve the same room (R1950)."""

from contextlib import nullcontext
from functools import cache
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.kernel import id_namespace

SALTS = ("-", "a", "b", "c", "d", "e")
_W = (BU, 0.5)
_GROUPS, _PER = 5, 4


class _Io(NamedTuple):
    X: Any


@fr.unit("sup-src", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Source", number="S-1")
def _source(u: Any) -> _Io:
    xd = u.terminal_strip("XD", "DEMO-TB-2.5", 2, interface=True)
    psu = u.device("T1", "DEMO-PSU-24")
    u.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    dc = u.dc_supply("S", psu)
    u.series(dc.plus, xd[1].inner, wire=_W)
    u.series(dc.minus, xd[2].inner, wire=_W)
    return _Io(xd)


def _load_unit(key: str, groups_n: int) -> Any:
    """The load unit with `groups_n` groups of `_PER` relays."""

    @fr.unit(key, revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Load", number="S-2")
    def load(u: Any) -> _Io:
        xc = u.terminal_strip("XC", "DEMO-TB-2.5", 2, interface=True)
        xg = u.terminal_strip("XG", "DEMO-TB-2.5", groups_n * _PER + 1, bridged=True)
        groups = []
        with u.function("IN", "IN") as g:
            fuse = u.device("FI", "DEMO-FUSE-DC-160")
            u.series(xc[1].inner, fuse[1], wire=_W)
            dc = u.dc_supply("S", plus=fuse[2], minus=xc[2].inner, voltage=24)
        groups.append(g)
        n = 1
        for gi in range(groups_n):
            with u.function(f"G{gi}", f"G{gi}") as g:
                for j in range(_PER):
                    relay = u.device(f"R{gi}{j}", "DEMO-RLY-2CO-24")
                    lamp = u.device(f"H{gi}{j}", "DEMO-LAMP-24")
                    u.series(dc.plus, relay.coil["A1"], wire=_W)
                    u.series(relay.coil["A2"], xg[n].inner, wire=_W)
                    u.series(dc.plus, relay.co_1[11], wire=_W)
                    u.series(relay.co_1[14], lamp["1"], wire=_W)
                    u.series(lamp["2"], xg[n].outer, wire=_W)
                    n += 1
            groups.append(g)
        u.layout.order(*groups)
        return _Io(xc)

    return load


_LOADS = {20: _load_unit("sup-load", _GROUPS), 16: _load_unit("sup-load16", 4)}


def _build(salt: str, relays: int) -> fr.BuildResult:
    with id_namespace(salt) if salt != "-" else nullcontext():
        d = fr.design("demo_parts", place="PLANT")
        d.location("PLANT", "Plant room")
        load = d.add(_LOADS[relays], "U2", place=None)
        source = d.add(_source, "U1", place=None)
        cable = d.cable("W2", "DEMO-CBL-4G1.5", length_m=5)
        d.series(source.X[1], cable, load.X[1], wire=1.5)
        d.series(source.X[2], cable, load.X[2], wire=1.5)
        return fr.build(d, unit_document("sup-src"), unit_document("sup-load" if relays == 20 else "sup-load16"))


@cache
def _built(salt: str) -> fr.BuildResult:
    return _build(salt, 20)


@cache
def _built_sixteen(salt: str) -> fr.BuildResult:
    return _build(salt, 16)


@pytest.mark.parametrize("salt", SALTS)
def test_every_connection_and_marker_is_drawn(salt: str) -> None:
    """Two unit documents: no CND, MARKER_UNPLACED, DANGLING_WIRE_END, RAIL_IDENTITY_SHARED or DRAWING_SHORTS_NETS."""
    codes = {f.code for f in fr.check(_built(salt))}
    assert codes & {"CONNECTION_NOT_DRAWN", "MARKER_UNPLACED", "DANGLING_WIRE_END", "RAIL_IDENTITY_SHARED", "DRAWING_SHORTS_NETS"} == set()


@pytest.mark.parametrize("salt", SALTS)
def test_sixteen_relays_stay_clean(salt: str) -> None:
    """The 4x4 fan that always fitted keeps no CND, MARKER_UNPLACED, DANGLING_WIRE_END, RAIL_IDENTITY_SHARED or DRAWING_SHORTS_NETS."""
    codes = {f.code for f in fr.check(_built_sixteen(salt))}
    assert codes & {"CONNECTION_NOT_DRAWN", "MARKER_UNPLACED", "DANGLING_WIRE_END", "RAIL_IDENTITY_SHARED", "DRAWING_SHORTS_NETS"} == set()
