"""Field case (KI-739): three starter outputs on one DO16 card and six valve coils on a second build with no ERROR.
With two cards the node conflict (R418) leaves two legs of one net on the driver node; they were two cross links of one name,
so the cut planned two tags per page cut and stage 8a raised `the end names no pin`."""

from contextlib import contextmanager, nullcontext
from functools import cache
from itertools import count
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.kernel import Severity, id_namespace

if TYPE_CHECKING:
    from collections.abc import Generator

SALTS = ("-", "a", "b", "c", "d", "e")
_W = (BU, 0.5)


class _Io(NamedTuple):
    pass


@fr.unit("demo-skid", revision=1, interface_version=1, date="2026-11-06", text="first", by="XX")
def _skid(d: Any) -> _Io:  # noqa: PLR0915  one linear repro shape
    rack = d.rack("R1")
    order: list[Any] = []
    di_ch = count(1)
    do_ch = (count(1), count(1))

    @contextmanager
    def group(tag: str, name: str) -> Generator[None]:
        with d.function(tag, name) as g:
            yield
        order.append(g)

    with d.function("MDI", "Digital inputs"):
        di = d.device("A11", "DEMO-PLC-DI-16", parent=rack)
    with d.function("MDO", "Digital outputs"):
        do = [d.device(f"A{k + 2}", "DEMO-PLC-DO-16", parent=rack) for k in (1, 2)]
    with group("G1", "Mains input"):
        xl = d.terminal_strip("XL", "DEMO-TB-2.5")
        runs = [xl.run(p, 8, bridged=True) for p in ("L1", "L2", "L3")]
        nrun = xl.run("N", 8, bridged=True)
    with group("G2", "24 V supply"):
        f1 = d.device("F1", "DEMO-MCB-2P")
        psu = d.device("T1", "DEMO-PSU-24")
        dc = d.dc_supply("S", psu)
        x24 = d.terminal_strip("X24", "DEMO-TB-FUSE-2.5", 29, bridged=True)
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 29, bridged=True)
        d.series(runs[0][6].outer, f1.pole_1, psu.input["L"], wire=(BU, 2.5))
        d.series(nrun[6].outer, f1.pole_2, psu.input["N"], wire=(BU, 2.5))
        d.series(dc.plus, x24[1].inner, wire=_W)
    qs, ovs = [], []
    for k in (1, 2):
        with group(f"PU{k}", f"Pump {k}"):
            q = d.device(f"QP{k}", "DEMO-CTR-3P-NC")
            f = d.device(f"FP{k}", "DEMO-MCB-3P")
            o = d.device(f"OP{k}", "DEMO-OVERLOAD-3P")
            m = d.device(f"MP{k}", "DEMO-MOTOR-4KW")
            w = d.cable(f"WP{k}", "DEMO-CBL-4G1.5", length_m=10)
            for n, pin in enumerate("UVW", 1):
                w.core(n, o.main[str(2 * n)], m.motor[pin])
        qs.append(q)
        ovs.append(o)
    with group("FA", "Fan"):
        q = d.device("QF", "DEMO-CTR-3P-NC")
        d.series(tuple(r[4].outer for r in runs), f.element, q.main, tuple(m.motor[p] for p in "UVW"), wire=(BU, 2.5))
    qs.append(q)
    ovs.append(None)
    for k in (1, 2, 3):
        with group(f"SC{k}", f"Starter control {k}"):
            sel = d.device(f"KM{k}", "DEMO-SEL-3P-24")
            s = d.device(f"SS{k}", "DEMO-PB-NO")
            fe = [x24[17 + 3 * (k - 1) + j].outer for j in range(3)]
            re = [x0[17 + 2 * (k - 1) + j].outer for j in range(2)]
            d.series(fe[0], qs[k - 1].coil, sel.co["12"], sel.co["11"], s.sw, re[0], wire=_W)
            d.series(sel.co["11"], sel.co["14"], getattr(do[0], f"do_{next(do_ch[0])}"), wire=_W)
            d.series(fe[2], qs[k - 1].aux_nc, getattr(di, f"di_{next(di_ch)}"), wire=_W)
            if ovs[k - 1] is not None:
                d.series(x24[19 + 3 * (k - 1)].inner, ovs[k - 1].aux, getattr(di, f"di_{next(di_ch)}"), wire=_W)
    with group("VR", "Valve relays"):
        for k in range(1, 7):
            r = d.device(f"KV{k}", "DEMO-RLY-4CO-24")
            d.series(getattr(do[1], f"do_{next(do_ch[1])}"), r.coil, dc.minus, wire=_W)
    with group("PLC", "Controller"):
        cpu = d.device("A0", "DEMO-PLC-CPU", parent=rack)
        d.series(x24[29].inner, cpu.power["24V"], wire=_W)
        d.series(cpu.power["0V"], x0[29].inner, wire=_W)
    d.layout.order(*order)
    return _Io()


@cache
def _built(salt: str) -> fr.BuildResult:
    with id_namespace(salt) if salt != "-" else nullcontext():
        d = fr.design("demo_parts")
        d.add(_skid, "U1")
        return fr.build(d, unit_document("demo-skid"))


def _errors(salt: str) -> list[str]:
    return sorted(f.code for f in fr.check(_built(salt)) if f.severity is Severity.ERROR)


def test_three_starter_outputs_and_six_valve_coils_on_two_output_cards_build_with_no_error() -> None:
    """KI-739: no ERROR at any salt (a net whose fan splits into two out legs is one cross link)."""
    assert [_errors(salt) for salt in SALTS] == [[] for _ in SALTS]
