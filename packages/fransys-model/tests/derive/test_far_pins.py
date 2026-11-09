"""`derive.far_pins`: the far port of each conductor at a set of ports, lowest far port first."""

from typing import TYPE_CHECKING

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.derive import far_pins, port_designation, stub_far
from fransys_model.derive.designation import _marking_counts, port_marking
from fransys_model.derive.designation_connector import connector_ports
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind, PortBoundary
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port


def _three_pins():
    plant = Plant()
    near, high, low, lone = (make_pin(plant, k, k.upper()) for k in ("n", "h", "l", "o"))
    plant.wire(near, high, key="to-high")
    plant.wire(low, near, key="to-low")
    return plant.model(), near, high, low, lone


def test_each_conductor_at_a_near_port_gives_its_far_port_by_stub_far_order() -> None:
    model, near, high, low, _ = _three_pins()
    assert far_pins(model, [near]) == ((near, high), (near, low))


def test_a_port_no_conductor_reaches_gives_no_pair() -> None:
    model, _, _, _, lone = _three_pins()
    assert far_pins(model, [lone]) == ()


def test_a_conductor_between_two_near_ports_gives_both_directions() -> None:
    model, near, high, _, _ = _three_pins()
    assert (near, high) in far_pins(model, [near, high])
    assert (high, near) in far_pins(model, [near, high])


def test_stub_far_names_the_first_pair() -> None:
    model, near, _, _, _ = _three_pins()
    found = stub_far(model, [near])
    assert (found[0][0], found[0][1]) == far_pins(model, [near])[0]


def test_stub_far_names_the_far_end_it_is_given_and_none_that_is_no_reach() -> None:
    """R1581: a stub end names its conductor, the last one included, whatever the first by designation is."""
    model, near, _, _, lone = _three_pins()
    _, second = far_pins(model, [near])
    found = stub_far(model, [near], [second[1]])
    assert [(end[0], end[1]) for end in found] == [second]
    assert stub_far(model, [near], [lone]) == ()


def _far_designations(suffix: str) -> list[str]:
    plant = Plant()
    near = make_pin(plant, "n" + suffix, "N")
    for k in "abcd":
        plant.wire(near, make_pin(plant, k + suffix, k.upper()), key="to-" + k + suffix)
    model = plant.model()
    return [port_designation(model, far) for _, far in far_pins(model, [near])]


def test_far_ends_print_in_designation_order_whatever_their_id_order() -> None:
    """model-0424: key salts that swap the far ports' id order give the same printed order."""
    printed = {tuple(_far_designations(str(n))) for n in range(8)}
    assert len(printed) == 1
    (only,) = printed
    assert len(only) == 4
    assert list(only) == sorted(only)


def _marked_item() -> tuple[Model, dict[str, Id[Port]]]:
    plant = Plant()
    function = plant.function(plant.item("q", designation="Q1"), "element")
    ports = {
        "plain": plant.port(function, "1", marking="P01"),
        "blank": plant.port(function, "2", marking=""),
        "line": plant.port(function, "N1", marking="N"),
        "load": plant.port(function, "N2", marking="N"),
    }
    return plant.model(), ports


def test_a_list_end_prints_the_marking_and_the_name_where_the_marking_is_empty_or_repeats() -> None:
    """R1794, R1796: the marking, else the name; a blank or a repeated marking prints the name."""
    model, ports = _marked_item()
    printed = {key: port_designation(model, port) for key, port in ports.items()}
    assert printed == {"plain": "-Q1:P01", "blank": "-Q1:2", "line": "-Q1:N1", "load": "-Q1:N2"}
    assert port_marking(model, ports["line"]) == port_marking(model, ports["load"]) == "N"


def _named_pins(*named: tuple[str, str, str], head_markings: tuple[str, ...] = ("1",)) -> tuple[Model, dict[str, Id[Port]]]:
    """Item U1 with connectors J1 and J2 (each holding header ports `head_markings`) and a role function `q`.

    Each `(port, connector, pin)` of `named` is a port of `q` whose template names that pin of that connector.
    """
    plant = Plant()
    item = plant.item("u", designation="U1")
    ports = {f"{c}.{m}": port for c in ("j1", "j2") for m, port in make_connector(plant, ("u", c), head_markings, marking=c.upper())[1].items()}
    role = plant.function(item, "q")
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("q",)), key=("q",), part=make_part(plant, "cp-q", "CP-q"), name="q", kind=FunctionKind.GENERIC
    )
    plant.add(template)
    for name, connector, pin in named:
        port_template = PortTemplate(
            id=make_id(PortTemplate, ("q", name)),
            key=("q", name),
            function=template.id,
            name=name,
            boundary=PortBoundary.GENERIC,
            connector=make_id(FunctionTemplate, ("u", connector, "template")),
            connector_pin=pin,
        )
        plant.add(port_template)
        ports[name] = plant.port(role, name, template=port_template.id)
    return plant.model(), ports


@pytest.mark.rule("DESIGNATION-SCHEME")
def test_two_ports_naming_one_pin_number_on_two_connectors_print_under_their_own_connector() -> None:
    """R1990: the pin prints under the connector the port names, so `P01` on J1 and J2 stays `P01`."""
    model, ports = _named_pins(("a", "j1", "P01"), ("b", "j2", "P01"), head_markings=("P09",))
    assert port_designation(model, ports["a"]) == "-U1-J1:P01"
    assert port_designation(model, ports["b"]) == "-U1-J2:P01"


def test_a_port_naming_a_header_pin_prints_the_headers_text_and_is_counted_once_under_it() -> None:
    """GAP-7: a port naming `j1.1` prints as the header port `j1.1` does, and the pin is counted once."""
    model, ports = _named_pins(("a", "j1", "1"))
    assert port_designation(model, ports["a"]) == port_designation(model, ports["j1.1"]) == "-U1-J1:1"
    assert _marking_counts(model)["-U1-J1", "1"] == 1
    assert _marking_counts(model)["-U1-J2", "1"] == 1


def test_a_connectors_ports_are_its_own_and_those_naming_a_pin_it_has_no_port_for() -> None:
    """GAP-8b: the one reader of a connector's ports (`connector_ports`) adds a named port only where no header port stands."""
    model, ports = _named_pins(("a", "j1", "1"), ("b", "j1", "2"))
    assert connector_ports(model, make_id(Function, ("u", "j1"))) == (ports["j1.1"], ports["b"])
