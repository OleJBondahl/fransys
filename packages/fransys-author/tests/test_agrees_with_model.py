"""The author's and the model's poles of every demo-skid function, against a written table (EL-5).

The expected pole pins are typed here, not computed by `poles_of_template`, so a change inside
that fact moves the code and not the table. A sideless function (a PLC analog channel, a terminal)
gives the author no poles; the model pairs its pins. A 3-phase motor's U, V, W are one pole each
in both (NS-2b: its terminals are not line and load ends).
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import fransys as fr
from fransys_author.surface._pairing import poles

from fransys_model.derive.pole_lists import poles_of
from fransys_model.vocab import Function, Port

SKID = Path(__file__).resolve().parents[3] / "examples" / "demo-skid" / "skid.py"


def _skid() -> tuple[fr.Design, fr.Draft]:
    spec = importlib.util.spec_from_file_location("agrees_skid", SKID)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.design()


def _author_functions(d: fr.Design) -> list[SimpleNamespace]:
    """The design's functions that have a part, shaped as `poles` reads them."""
    records = list(d.draft().records())
    ports = [r for r in records if isinstance(r, Port)]
    return [
        SimpleNamespace(
            id=f.id,
            name=f.name,
            kind=f.kind,
            ports=tuple(p for p in ports if p.function == f.id),
        )
        for f in records
        if isinstance(f, Function) and f.template is not None
    ]


_Poles = tuple[tuple[str, str], ...]
_Row = tuple[_Poles, _Poles]  # (author poles, model poles)


def _same(poles: _Poles) -> _Row:
    return poles, poles


_P1: _Poles = (("1", "2"),)
_P3: _Poles = (("1", "2"), ("3", "4"), ("5", "6"))
_CO1: _Poles = (("11", "12"), ("11", "14"))
# (function name, kind) -> the rows the skid has for it
_TABLE: dict[tuple[str, str], tuple[_Row, ...]] = {
    ("aux", "contact_nc"): (_same((("95", "96"),)),),
    ("aux", "contact_no"): (_same((("13", "14"),)),),
    ("aux_nc", "contact_nc"): (_same((("21", "22"),)),),
    ("co_1", "contact_co"): ((_CO1, _CO1),),
    ("co_2", "contact_co"): (_same((("21", "22"), ("21", "24"))),),
    ("coil", "coil"): (_same((("A1", "A2"),)),),
    ("element", "protection"): ((_P1, _P1), (_P3, _P3)),
    ("lamp", "load"): ((_P1, _P1),),
    ("main", "contact_no"): ((_P3, _P3),),
    ("main", "protection"): ((_P3, _P3),),
    ("motor", "actuator"): (_same((("U", "U"), ("V", "V"), ("W", "W"))),),
    ("terminal", "terminal"): (((), (("external", "internal"),)),),
}
_ANALOG = {"ai_1": ("1", "2"), "ai_2": ("5", "6"), "ai_3": ("3", "4"), "ai_4": ("7", "8")}


def _rows(name: str, kind: str) -> tuple[_Row, ...]:
    """The written table's rows; a digital channel is the one pin `N` of `di_N` or `do_N`."""
    if kind != "plc_channel":
        return _TABLE[name, kind]
    if name in _ANALOG:
        return (((), (_ANALOG[name],)),)
    pin = name.split("_")[1]
    return (_same(((pin, pin),)),)


def test_author_and_model_poles_of_every_skid_function() -> None:
    d, document = _skid()
    model = fr.build(d, document).model
    seen = set()
    for fn in _author_functions(d):
        pairs = poles(d._pairing_facts, fn)  # ty: ignore[invalid-argument-type] -- a shim shaped like Fn
        author = tuple((a.name, b.name) for a, b in pairs)
        found = poles_of(model, [p.template for p in fn.ports if p.template is not None])
        mine = tuple((p.ends[0].name, p.ends[1].name) for p in found)
        assert (author, mine) in _rows(fn.name, fn.kind.value)
        seen.add((fn.name, fn.kind.value))
    assert set(_TABLE) <= seen
    assert any(not rows[0][0] for rows in map(_rows_of, seen))


def _rows_of(key: tuple[str, str]) -> tuple[_Row, ...]:
    return _rows(*key)
