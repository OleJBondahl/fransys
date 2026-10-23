"""`derive.series_parallel`: one series-parallel tree per region of the wiring (SERIES-PARALLEL)."""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.rows_series_parallel import ParallelRow, SeriesRow
from fransys_model.derive.series_parallel import series_parallel
from fransys_model.derive.series_parallel_reduce import SINK, SOURCE, reduce_region
from fransys_model.layout import Side
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Port

# Hand-written facings (not read from a symbol): the input end N, the output end S.
_SIDES = {
    "input": Side.N,
    "output": Side.S,
    "in_1": Side.N,
    "in_2": Side.N,
    "out": Side.S,
    "A": Side.N,
    "B": Side.S,
    "1": Side.N,
    "2": Side.S,
}


def _wire(d: fr.Design, a: Any, b: Any) -> None:
    d.detail.wire(a, b, wire=(BU, 0.5))


def _ends(model: fr.Model, tags: set[str]) -> dict[Id[Port], tuple[str, Side]]:
    """Each port of the items tagged `tags`: its tag as the symbol key, its side by name."""
    out = {}
    for port in ports(model).values():
        function = functions(model)[port.function]
        tag = items(model)[function.item].key[-1].rsplit("/", 1)[-1]
        side = _SIDES.get(function.name) or _SIDES.get(port.name)
        if tag in tags and side is not None:  # U1's dc_ok contact is wired nowhere
            out[port.id] = (tag, side)
    return out


def _psus(d: fr.Design) -> tuple[Any, Any, Any]:
    """T1 and T2 into the redundancy module U1 (the I3 plant, its strips left out)."""
    psus = [d.device(tag, "DEMO-PSU-24") for tag in ("T1", "T2")]
    module = d.device("U1", "DEMO-RED-2IN")
    for psu, group, n in ((psus[0], module.in_1, "1"), (psus[1], module.in_2, "2")):
        _wire(d, psu.output["+"], group[f"{n}+"])
        _wire(d, psu.output["-"], group[f"{n}-"])
    return psus[0], psus[1], module


@pytest.fixture(scope="module")
def plants() -> dict[str, fr.Model]:
    """One model per plant: the I3 plant, a control circuit, a hub and a bridge."""
    found = {}
    authors = (("i3", _i3), ("control", _control), ("hub", _hub), ("bridge", _bridge))
    for name, author in (*authors, ("pair", _pair), ("rails", _rails)):
        d = fr.design("demo_parts")
        d.location("L0", "Workshop")
        with d.function("G", "Group"):
            author(d)
        found[name] = fr.build(d).model
    return found


def _i3(d: fr.Design) -> None:
    _psus(d)


def _buttons(d: fr.Design, *tags: str) -> list[Any]:
    return [d.device(tag, "DEMO-PB-NO", place="L0").sw for tag in tags]


def _control(d: fr.Design) -> None:
    """S1, then S2 beside S3 and S4 in series, then the lamp H1."""
    s1, s2, s3, s4 = _buttons(d, "S1", "S2", "S3", "S4")
    h1 = d.device("H1", "DEMO-LAMP-24", place="L0").lamp
    for a, b in ((s1["B"], s2["A"]), (s1["B"], s3["A"]), (s3["B"], s4["A"])):
        _wire(d, a, b)
    for a, b in ((s2["B"], h1["1"]), (s4["B"], h1["1"])):
        _wire(d, a, b)


def _hub(d: fr.Design) -> None:
    """U1 wired by three functions is a hub; H1 and H2 hang below its output."""
    _, _, module = _psus(d)
    h1, h2 = (d.device(t, "DEMO-LAMP-24", place="L0").lamp for t in ("H1", "H2"))
    _wire(d, module.out["+"], h1["1"])
    _wire(d, h1["2"], h2["1"])


def _pair(d: fr.Design) -> None:
    """S1 beside S2, both ends wired together and to nothing else."""
    s1, s2 = _buttons(d, "S1", "S2")
    _wire(d, s1["A"], s2["A"])
    _wire(d, s1["B"], s2["B"])


def _rails(d: fr.Design) -> None:
    """H1 from rail to rail, and S1 then H2 from rail to rail, on T1's 24 V supply."""
    psu = d.device("T1", "DEMO-PSU-24")
    d.dc_supply("S", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    (s1,) = _buttons(d, "S1")
    h1, h2 = (d.device(t, "DEMO-LAMP-24", place="L0").lamp for t in ("H1", "H2"))
    for a, b in ((psu.output["+"], h1["1"]), (h1["2"], psu.output["-"])):
        _wire(d, a, b)
    for a, b in ((psu.output["+"], s1["A"]), (s1["B"], h2["1"]), (h2["2"], psu.output["-"])):
        _wire(d, a, b)


def _bridge(d: fr.Design) -> None:
    """A Wheatstone shape: S4 joins the middles of S2-S5 and S3-S6."""
    s = dict(zip("123456", _buttons(d, "S1", "S2", "S3", "S4", "S5", "S6"), strict=True))
    h1 = d.device("H1", "DEMO-LAMP-24", place="L0").lamp
    pairs = (("1", "2"), ("1", "3"), ("2", "4"), ("2", "5"), ("4", "3"), ("3", "6"))
    for a, b in pairs:
        _wire(d, s[a]["B"], s[b]["A"])
    for a in ("5", "6"):
        _wire(d, s[a]["B"], h1["1"])


@pytest.mark.rule("SERIES-PARALLEL")
def test_two_supplies_into_a_redundancy_module_are_a_parallel_then_the_module(plants) -> None:
    """The worked example: catches T1 and T2 read as a chain through U1, or U1 as a hub."""
    found = series_parallel(plants["i3"], _ends(plants["i3"], {"T1", "T2", "U1"}))
    pair = ParallelRow(parts=("T1", "T2"))
    assert found.regions == (SeriesRow(parts=(pair, "U1")),)
    assert found.bridges == ()


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_nested_control_circuit_keeps_its_inner_series_in_one_lane(plants) -> None:
    """Catches the inner series flattened into the parallel, or the parallel lost."""
    model = plants["control"]
    found = series_parallel(model, _ends(model, {"S1", "S2", "S3", "S4", "H1"}))
    inner = ParallelRow(parts=("S2", SeriesRow(parts=("S3", "S4"))))
    assert found.regions == (SeriesRow(parts=("S1", inner, "H1")),)


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_hub_ends_the_region_and_the_series_below_it_stands_alone(plants) -> None:
    """Catches a hub kept as a part: U1 is wired by three functions, so it is in no series."""
    model = plants["hub"]
    found = series_parallel(model, _ends(model, {"T1", "T2", "U1", "H1", "H2"}))
    assert found.regions == (SeriesRow(parts=("H1", "H2")),)


@pytest.mark.rule("SERIES-PARALLEL")
def test_two_symbols_side_by_side_with_nothing_in_series_are_one_region(plants) -> None:
    """Catches a region of one parallel dropped because no node of it is inner."""
    found = series_parallel(plants["pair"], _ends(plants["pair"], {"S1", "S2"}))
    assert found.regions == (SeriesRow(parts=(ParallelRow(parts=("S1", "S2")),)),)


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_rail_ends_a_region_and_joins_nothing(plants) -> None:
    """Catches a rail read as wiring: it would join every load on it into one region."""
    model = plants["rails"]
    found = series_parallel(model, _ends(model, {"T1", "S1", "H1", "H2"}))
    assert found.regions == (SeriesRow(parts=("S1", "H2")),)
    assert found.bridges == ()


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_bridge_gives_no_series_and_names_its_symbols(plants) -> None:
    """Catches a bridge forced into a tree, or its symbols dropped."""
    model = plants["bridge"]
    tags = {"S1", "S2", "S3", "S4", "S5", "S6", "H1"}
    found = series_parallel(model, _ends(model, tags))
    assert found.regions == ()
    assert found.bridges == (("H1", "S1", "S2", "S3", "S4", "S5", "S6"),)


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_lone_leaf_is_its_own_part_and_a_parallel_takes_natural_order() -> None:
    """Catches a leaf wrapped twice, or parallel parts kept in arrival order."""
    assert reduce_region([(SOURCE, SINK, "K1")]) == "K1"
    merged = reduce_region([(SOURCE, SINK, "S10"), (SOURCE, SINK, "S2")])
    assert merged == ParallelRow(parts=("S2", "S10"))
