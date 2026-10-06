"""`CONNECTOR_WIRED_WITHOUT_MATE`: a conductor lands directly on a nested unit's gendered
boundary connector (decision model-0116; `vocab/validators/units.py`).
"""

from typing import TYPE_CHECKING

import pytest
from plant import Plant

from fransys_model.kernel import Finding, Id, Severity, make_id
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.enums import FunctionKind, Gender
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.templates import FunctionTemplate
from fransys_model.vocab.validators.units import CONNECTOR_WIRED_WITHOUT_MATE, check_units

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Port


def _connector(
    plant: Plant, item: Id, name: str, gender: Gender | None, *, stated: bool = True
) -> tuple[Id[Function], Id[Port]]:
    """A connector function of `item` whose template carries a facet of `gender`."""
    key = (item.value, name)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, key),
        key=key,
        part=plant.part(f"conn-{name}"),
        name=name,
        kind=FunctionKind.CONNECTOR,
    )
    plant.add(template)
    if stated:
        plant.add(
            ConnectorFacet(
                id=make_id(ConnectorFacet, key),
                key=key,
                subject=template.id,
                style="header",
                pincount=1,
                gender=gender,
            )
        )
    function = plant.function(item, name, template=template.id, kind=FunctionKind.CONNECTOR)
    return function, plant.port(function, "1")


def _board_wired_by_container(
    gender: Gender | None, *, stated: bool = True, direct: bool = True
) -> tuple[Id[Function], list[Finding]]:
    """A container unit holding a board unit whose boundary connector `x1` has `gender`.

    The container's plug `p1` is wired to `x1` directly (`direct`), or to nothing on `x1`.
    """
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    board = plant.unit("board", name="board", parent=cabinet)
    board_item = plant.item("board-item", unit=board)
    cabinet_item = plant.item("cabinet-item", unit=cabinet)
    x1, x1_port = _connector(plant, board_item, "x1", gender, stated=stated)
    _, p1_port = _connector(plant, cabinet_item, "p1", Gender.FEMALE)
    plant.boundary(board, x1)
    if direct:
        plant.wire(p1_port, x1_port, key="direct")
    findings = [f for f in check_units(plant.model()) if f.code == CONNECTOR_WIRED_WITHOUT_MATE]
    return x1, findings


@pytest.mark.parametrize("gender", [Gender.MALE, Gender.FEMALE])
def test_a_wire_onto_a_gendered_boundary_connector_warns(gender: Gender) -> None:
    x1, findings = _board_wired_by_container(gender)
    (finding,) = findings
    assert finding.severity == Severity.WARNING
    assert x1 in finding.subjects
    assert make_id(Conductor, ("direct",)) in finding.subjects
    assert gender.value in finding.message


@pytest.mark.parametrize(
    ("gender", "stated"), [(Gender.NEUTRAL, True), (None, True), (None, False)]
)
def test_a_neutral_or_unstated_gender_takes_the_wire_silently(
    gender: Gender | None, *, stated: bool
) -> None:
    _, findings = _board_wired_by_container(gender, stated=stated)
    assert findings == []


def test_a_gendered_boundary_connector_wired_by_nothing_is_silent() -> None:
    _, findings = _board_wired_by_container(Gender.MALE, direct=False)
    assert findings == []


def test_a_wire_inside_the_child_unit_is_silent() -> None:
    plant = Plant()
    board = plant.unit("board", name="board")
    item = plant.item("board-item", unit=board)
    x1, x1_port = _connector(plant, item, "x1", Gender.MALE)
    _, inner_port = _connector(plant, item, "j1", Gender.FEMALE)
    plant.boundary(board, x1)
    plant.wire(inner_port, x1_port, key="inside")
    findings = [f for f in check_units(plant.model()) if f.code == CONNECTOR_WIRED_WITHOUT_MATE]
    assert findings == []


def test_a_mate_to_the_boundary_connector_is_silent() -> None:
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    board = plant.unit("board", name="board", parent=cabinet)
    x1, _ = _connector(plant, plant.item("board-item", unit=board), "x1", Gender.MALE)
    p1, _ = _connector(plant, plant.item("cabinet-item", unit=cabinet), "p1", Gender.FEMALE)
    plant.boundary(board, x1)
    plant.mate(p1, x1)
    findings = [f for f in check_units(plant.model()) if f.code == CONNECTOR_WIRED_WITHOUT_MATE]
    assert findings == []
