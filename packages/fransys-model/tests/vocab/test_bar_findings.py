"""`BAR_NOT_PE`: a port of a bar function whose role is not `pe` is an ERROR (PE-BAR B5)."""

from plant import Plant

from fransys_model.kernel import Finding, Severity, make_id
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import FunctionKind, PortRole
from fransys_model.vocab.validators.bars import BAR_NOT_PE, check_bars


def _bar(roles: dict[str, PortRole]) -> list[Finding]:
    plant = Plant()
    item = plant.item("pe1")
    function = plant.function(item, "pe", kind=FunctionKind.BAR)
    for name, role in roles.items():
        key = ("pe1", "pe", name)
        plant.add(
            Port(
                id=make_id(Port, key),
                key=key,
                function=function,
                template=None,
                name=name,
                role=role,
            )
        )
    return [f for f in check_bars(plant.model()) if f.code == BAR_NOT_PE]


def test_a_generic_port_on_a_bar_is_an_error_that_names_the_fix() -> None:
    (finding,) = _bar({"1": PortRole.PE, "3": PortRole.GENERIC})
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (make_id(Port, ("pe1", "pe", "3")),)
    assert 'role = "pe"' in finding.message
    assert "copper bar drawing" in finding.message


def test_a_bar_of_pe_ports_gives_no_finding() -> None:
    assert _bar({"1": PortRole.PE, "2": PortRole.PE}) == []
    assert len(_bar({"1": PortRole.GENERIC})) == 1  # the same plant with a generic port fires


def test_a_generic_port_off_a_bar_gives_no_finding() -> None:
    plant = Plant()
    plant.pin("k1", "coil", "A1")
    assert check_bars(plant.model()) == ()
