"""F9: a port's pole side and conductor mark, from its marking or as stated (parts-0010)."""

import itertools
from pathlib import Path

import fransys_parts
import pytest
from fransys_parts import PartLibraryError

from fransys_model.kernel import freeze
from fransys_model.vocab import (
    ConductorMark,
    PoleSide,
    PortTemplate,
    function_templates,
    parts,
    port_templates,
)

DEMO = (
    next(p for p in Path(__file__).resolve().parents if (p / "examples").is_dir())
    / "examples"
    / "demo-parts"
    / "demo_parts"
)
_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_HEAD = (
    'schema = 1\n\n[part]\nmpn = "X-1"\nmanufacturer = "Demo"\ndescription = "d"\n'
    'category = "generic"\nclass_code = "X"\n'
)
_roots = itertools.count()


def _facts(model, name):
    """`(pole_side, conductor_mark)` of the one port template called `name`."""
    (port,) = (p for p in model.tables["port_template"].values() if p.name == name)
    return port.pole_side, port.conductor_mark


def _model(tmp_path, body):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(_HEAD + body)
    return freeze(fransys_parts.load_path(root))


def _function(kind, ports, links=""):
    return f'\n[[function]]\nname = "f"\nkind = "{kind}"\nports = [{ports}]\n{links}'


def _ports(model, function_kind):
    return {
        p.name: (p.pole_side, p.conductor_mark)
        for p in model.tables["port_template"].values()
        if isinstance(p, PortTemplate)
        and model.tables["function_template"][p.function].kind.value == function_kind
    }


def test_the_demo_contactor_poles_take_side_from_odd_and_even_markings():
    ports = _ports(freeze(fransys_parts.load_path(DEMO)), "contact_no")
    assert ports["1"] == (PoleSide.LINE, None)
    assert ports["2"] == (PoleSide.LOAD, None)
    assert ports["13"] == (PoleSide.LINE, None)
    assert ports["14"] == (PoleSide.LOAD, None)


def test_the_demo_coil_a1_is_line_and_a2_is_load():
    ports = _ports(freeze(fransys_parts.load_path(DEMO)), "coil")
    assert ports["A1"][0] is PoleSide.LINE
    assert ports["A2"][0] is PoleSide.LOAD


def test_the_demo_motor_ends_are_the_three_phases_and_pe_has_no_mark():
    ports = _ports(freeze(fransys_parts.load_path(DEMO)), "actuator")
    assert (ports["U"][1], ports["V"][1], ports["W"][1]) == (
        ConductorMark.L1,
        ConductorMark.L2,
        ConductorMark.L3,
    )
    assert ports["PE"] == (None, None)


def test_the_demo_psu_has_n_and_dc_polarity_from_its_markings():
    model = freeze(fransys_parts.load_path(DEMO))
    assert _ports(model, "load")["N"][1] is ConductorMark.N
    supply = _ports(model, "supply")
    assert supply["+"][1] is ConductorMark.L_PLUS
    assert supply["-"][1] is ConductorMark.L_MINUS


def test_the_demo_plc_module_states_its_supply_pins():
    model = freeze(fransys_parts.load_path(DEMO))
    assert _facts(model, "24V")[1] is ConductorMark.L_PLUS
    assert _facts(model, "0V")[1] is ConductorMark.L_MINUS


def test_an_even_marking_not_on_a_pole_link_states_nothing(tmp_path):
    model = _model(tmp_path, _function("generic", '{ name = "2", role = "generic" }'))
    assert _facts(model, "2") == (None, None)


def test_a_protective_link_pole_takes_side_from_its_markings(tmp_path):
    ports = '{ name = "1", role = "generic" }, { name = "2", role = "generic" }'
    links = 'links = [{ a = "1", b = "2", kind = "protective" }]'
    model = _model(tmp_path, _function("protection", ports, links))
    assert _facts(model, "1")[0] is PoleSide.LINE
    assert _facts(model, "2")[0] is PoleSide.LOAD


def test_a_stated_value_wins_over_the_marking(tmp_path):
    ports = (
        '{ name = "1", role = "generic", side = "load", conductor = "N" }, '
        '{ name = "2", role = "generic", side = "line" }'
    )
    links = 'links = [{ a = "1", b = "2", kind = "switched", rest = "open" }]'
    model = _model(tmp_path, _function("switch", ports, links))
    assert _facts(model, "1") == (PoleSide.LOAD, ConductorMark.N)
    assert _facts(model, "2")[0] is PoleSide.LINE


def test_a_stated_conductor_wins_over_the_name(tmp_path):
    ports = '{ name = "U", role = "generic", conductor = "L3" }'
    model = _model(tmp_path, _function("actuator", ports))
    assert _facts(model, "U")[1] is ConductorMark.L3


def test_a_part_stating_conductor_pe_fails_to_load(tmp_path):
    body = _function("generic", '{ name = "E", role = "pe", conductor = "PE" }')
    with pytest.raises(PartLibraryError) as excinfo:
        _model(tmp_path, body)
    assert "ENUM_VALUE" in {finding.code for finding in excinfo.value.findings}


def test_a_bad_side_value_is_refused(tmp_path):
    body = _function("generic", '{ name = "1", role = "generic", side = "top" }')
    with pytest.raises(PartLibraryError):
        _model(tmp_path, body)


def test_a_stated_conductor_m_loads_as_the_mid_conductor(tmp_path):
    model = _model(
        tmp_path, _function("actuator", '{ name = "X", role = "generic", conductor = "M" }')
    )
    assert _facts(model, "X")[1] is ConductorMark.M


def test_the_demo_three_pole_parts_carry_pole_sides_and_conductors():
    """EA-PARTS-MODULE: the demo breaker and overload state line/load and L1..L3 per pole."""
    model = freeze(fransys_parts.load_path(DEMO))
    for mpn in ("DEMO-MCB-3P", "DEMO-OVERLOAD-3P"):
        (part,) = (p for p in parts(model).values() if p.mpn == mpn)
        functions = {f.id for f in function_templates(model).values() if f.part == part.id}
        ports = [
            p
            for p in port_templates(model).values()
            if p.function in functions and p.name in "123456"
        ]
        facts = {p.name: (p.pole_side, p.conductor_mark) for p in ports}
        assert facts["1"] == (PoleSide.LINE, ConductorMark.L1)
        assert facts["4"] == (PoleSide.LOAD, ConductorMark.L2)
        assert facts["5"] == (PoleSide.LINE, ConductorMark.L3)
        assert len(facts) == 6


_TWO_PINS = (
    '{ name = "a", marking = "1", role = "generic" }, '
    '{ name = "b", marking = "2", role = "generic" }'
)


def test_an_overload_main_path_takes_side_from_its_markings(tmp_path):
    """A protection function's conductive link is a pole too (parts-0012, F9)."""
    ports = _TWO_PINS
    links = 'links = [{ a = "a", b = "b", kind = "conductive" }]'
    model = _model(tmp_path, _function("protection", ports, links))
    assert _facts(model, "a")[0] is PoleSide.LINE
    assert _facts(model, "b")[0] is PoleSide.LOAD


def test_a_terminals_conductive_link_states_no_side(tmp_path):
    ports = _TWO_PINS
    links = 'links = [{ a = "a", b = "b", kind = "conductive" }]'
    model = _model(tmp_path, _function("terminal", ports, links))
    assert _facts(model, "a")[0] is None
