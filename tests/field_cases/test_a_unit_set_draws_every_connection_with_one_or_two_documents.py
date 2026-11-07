"""Field case: a unit set draws every connection with the unit document alone and with the system document beside it.
A second document widens every reference marker (`widest_scope`); the consumer's 54-page build then shows CONNECTION_NOT_DRAWN 1
on a cross-page wire (KI-749 WIDE-MARKER-CND, not reproduced here)."""

from contextlib import nullcontext
from functools import cache
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import system_document, unit_document
from fransys.colours import BK, RD

from fransys_model.kernel import id_namespace

SALTS = ("-", "a", "b", "c", "d", "e")
_CHAINS = 12


class _Io(NamedTuple):
    X1: Any
    X2: Any


@fr.unit("wide-chain", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Wide chain", number="W-1")
def _wide_chain(u: Any) -> _Io:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", _CHAINS, interface=True)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5", _CHAINS, interface=True)
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5", _CHAINS)
    for b in range(_CHAINS):
        with u.function(f"P{b}", f"Power {b}"):
            m = u.device(f"Q{b}", "DEMO-MCB-2P")
            f = u.device(f"F{b}", "DEMO-FUSE-DC-160")
        with u.function(f"C{b}", f"Control {b}"):
            k = u.device(f"K{b}", "DEMO-CONTACTOR-DC")
            r = u.device(f"R{b}", "DEMO-HEATER-24")
        u.series(x1[b + 1].inner, m.pole_1, f.element, k.pole, x2[b + 1].inner, wire=(RD, 100))
        u.series(k.pole[2], r.load["+"], wire=(RD, 100))
        u.series(r.load["-"], x3[b + 1], wire=(BK, 1.5))
    return _Io(x1, x2)


@cache
def _built(salt: str, *, with_system: bool) -> fr.BuildResult:
    with id_namespace(salt) if salt != "-" else nullcontext():
        d = fr.design("demo_parts")
        d.add(_wide_chain, "U1", place=None)
        documents = [unit_document("wide-chain"), *([system_document()] if with_system else [])]
        return fr.build(d, *documents)


@pytest.mark.parametrize("with_system", [False, True])
@pytest.mark.parametrize("salt", SALTS)
def test_every_connection_is_drawn(salt: str, *, with_system: bool) -> None:
    """The unit document alone and with the system document: no CONNECTION_NOT_DRAWN."""
    codes = [f.code for f in fr.check(_built(salt, with_system=with_system))]
    assert codes.count("CONNECTION_NOT_DRAWN") == 0
