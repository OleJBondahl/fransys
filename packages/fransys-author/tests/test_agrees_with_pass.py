"""The author's PLC channel pick against `allocate_plc`'s binding for the same taken set (EL-6).

Two identical designs: one the author wires (`d.series` takes the lowest free channel), one left
unwired with the same requests, for the pass to bind. Both use `plc_channel_tie`, `channel_takes`.
"""

import pytest
from fransys_author.surface import AI, DI, DO, design

from fransys_model.derive.passes.plc_allocation import allocate_plc
from fransys_model.kernel import freeze, make_id, merge
from fransys_model.vocab import PlcBindingFacet
from fransys_model.vocab.tables import facets_of

from .conftest import _ORIGIN
from .equivalence.series_parts import series_library
from .surface.test_series_channels import WIRE, _module

IO, MIX = "TEST-PLC-IO", "TEST-PLC-MIX"


@pytest.fixture(scope="module")
def plc_lib():
    draft = series_library()
    _module(draft, "TEST-PLC-IO", ("di_1", "di_2", "do_1", "do_2"))
    _module(draft, "TEST-PLC-MIX", ("di_1", "ai_1", "do_1"))
    return draft


# (module, steps (way, signal, tag), fixed channel of the first step or None)
CASES = {
    "inputs and outputs": (IO, (("in", DI, "S1"), ("out", DO, "K1"), ("in", DI, "S2")), None),
    "all four taken": (IO, (("in", DI, "S1"), ("in", DI, "S2"), ("out", DO, "K1")), None),
    "mixed kinds": (MIX, (("in", AI, "S1"), ("in", DI, "S2"), ("out", DO, "K1")), None),
    "a fixed channel": (IO, (("in", DI, "S1"), ("in", DI, "S2")), "di_1"),
}


def _built(draft, module, steps):
    d = design(draft, place="C1")
    a1 = d.device("A1", module)
    fns = []
    for way, signal, tag in steps:
        fn = d.device(tag, "TEST-BTN-NO" if way == "in" else "TEST-KM-3P")
        fns.append(fn.contact if way == "in" else fn.coil)
        fns[-1].plc(signal, tag)
    return d, a1, fns


def _author_picks(draft, module, steps, fixed):
    d, a1, fns = _built(draft, module, steps)
    picks = {}
    for i, ((way, _, _), fn) in enumerate(zip(steps, fns, strict=True)):
        before = set(d._taken_channels)
        end = getattr(a1, fixed) if i == 0 and fixed else a1
        d.series(fn, end, wire=WIRE) if way == "in" else d.series(end, fn, wire=WIRE)
        (taken,) = set(d._taken_channels) - before
        picks[fn._fn.id] = taken
    return picks


def _pass_picks(draft, module, steps, fixed):
    d, a1, fns = _built(draft, module, steps)
    if fixed:
        key = (*fns[0]._fn.key, "plc_binding")
        binding = PlcBindingFacet(
            id=make_id(PlcBindingFacet, key), key=key, subject=fns[0]._fn.id,
            channel=getattr(a1, fixed)._fn.id,
        )  # fmt: skip
        d.draft().add(binding, origin=_ORIGIN)
    model, _ = allocate_plc(freeze(merge(draft, d.draft())))
    return {b.subject: b.channel for b in facets_of(model, PlcBindingFacet).values()}


@pytest.mark.parametrize("case", CASES)
def test_the_author_takes_the_channel_the_pass_binds(plc_lib, case: str) -> None:
    module, steps, fixed = CASES[case]
    author = _author_picks(plc_lib, module, steps, fixed)
    assert author == _pass_picks(plc_lib, module, steps, fixed)
