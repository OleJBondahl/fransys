"""WP10 tests: `vocab.facets` (ROADMAP WP10, design/facets.md)."""

from decimal import Decimal

import pytest

from fransys_model.kernel import Draft, FreezeError, Id, Model, Origin, Record, freeze
from fransys_model.vocab.enums import Gender, PartCategory, SignalType
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.pcb import FootprintFacet, PcbFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.facets.supply import SupplyFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import Part

_SUBJECT = Id(kind="item", value="1" * 32)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_facets.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def test_terminal_facet_has_the_designed_fields() -> None:
    """`TerminalFacet` carries `group`, `index` (design/facets.md)."""
    facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="2" * 32),
        key=("examples", "x03", "l1-1", "terminal"),
        subject=_SUBJECT,
        group="L1",
        index=1,
    )
    assert (facet.group, facet.index) == ("L1", 1)


def test_plc_channel_facet_has_the_designed_fields() -> None:
    """`PlcChannelFacet` carries `signal`, `channel` (design/facets.md)."""
    facet = PlcChannelFacet(
        id=Id(kind="facet.plc_channel", value="3" * 32),
        key=("examples", "di-module", "ch3", "plc_channel"),
        subject=Id(kind="function_template", value="4" * 32),
        signal=SignalType.DI,
        channel=3,
    )
    assert (facet.signal, facet.channel) == (SignalType.DI, 3)


def test_plc_request_facet_has_the_designed_fields() -> None:
    """`PlcRequestFacet` carries `signal`, `signal_name`, `priority` (design/facets.md and
    design/examples.md 11)."""
    facet = PlcRequestFacet(
        id=Id(kind="facet.plc_request", value="5" * 32),
        key=("examples", "transmitter-1", "plc_request"),
        subject=Id(kind="function", value="6" * 32),
        signal=SignalType.AI_CURRENT,
        signal_name="Pos",
        priority=1,
    )
    assert facet.signal_name == "Pos"


def test_plc_binding_facet_has_the_designed_fields() -> None:
    """`PlcBindingFacet` carries `channel`, written only by the allocation pass (facets.md)."""
    channel = Id(kind="function", value="7" * 32)
    facet = PlcBindingFacet(
        id=Id(kind="facet.plc_binding", value="8" * 32),
        key=("examples", "transmitter-1", "plc_binding"),
        subject=Id(kind="function", value="6" * 32),
        channel=channel,
    )
    assert facet.channel == channel


def test_scaling_facet_has_the_designed_fields() -> None:
    """`ScalingFacet` carries `unit`, `raw_min`, `raw_max`, `eng_min`, `eng_max` (facets.md)."""
    facet = ScalingFacet(
        id=Id(kind="facet.scaling", value="9" * 32),
        key=("examples", "transmitter-1", "scaling"),
        subject=Id(kind="function", value="6" * 32),
        unit="m",
        raw_min=4,
        raw_max=20,
        eng_min=Decimal(0),
        eng_max=Decimal(5),
    )
    assert facet.eng_max == Decimal(5)


def test_cable_product_facet_has_the_designed_fields() -> None:
    """`CableProductFacet` carries `core_colours`, `gauge_mm2`, `shielded`; the count is `len`."""
    facet = CableProductFacet(
        id=Id(kind="facet.cable_product", value="a" * 32),
        key=("examples", "cable_4core", "cable_product"),
        subject=Id(kind="part", value="b" * 32),
        core_colours=("brown", "black", "grey", "blue"),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    assert (facet.core_colours, facet.gauge_mm2, facet.shielded) == (
        ("brown", "black", "grey", "blue"),
        Decimal("1.5"),
        False,
    )
    assert not hasattr(facet, "core_count")


def test_cable_facet_has_the_designed_fields() -> None:
    """`CableFacet` carries `length_mm`, `None` until measured (facets.md)."""
    facet = CableFacet(
        id=Id(kind="facet.cable", value="c" * 32),
        key=("examples", "w012", "cable"),
        subject=Id(kind="item", value="d" * 32),
        length_mm=None,
    )
    assert facet.length_mm is None


def test_core_facet_has_the_designed_fields() -> None:
    """`CoreFacet` carries `index` only; the product has the colour (SC4, connectivity.md)."""
    facet = CoreFacet(
        id=Id(kind="facet.core", value="e" * 32),
        key=("examples", "w012", "core-1"),
        subject=Id(kind="conductor", value="f" * 32),
        index=1,
    )
    assert facet.index == 1


def test_wire_facet_has_the_designed_fields() -> None:
    """`WireFacet` carries `colour`, `gauge_mm2`, `length_mm`, `label` (design/facets.md)."""
    facet = WireFacet(
        id=Id(kind="facet.wire", value="1" * 32),
        key=("examples", "w1", "wire"),
        subject=Id(kind="conductor", value="2" * 32),
        colour="blue",
        gauge_mm2=Decimal("0.75"),
        length_mm=250,
        label="W1",
    )
    assert facet.label == "W1"


def test_connector_facet_has_the_designed_fields() -> None:
    """`ConnectorFacet` carries `style`, `pincount`, `gender` (facets.md and examples.md)."""
    facet = ConnectorFacet(
        id=Id(kind="facet.connector", value="3" * 32),
        key=("examples", "harness", "j1", "connector"),
        subject=Id(kind="function_template", value="4" * 32),
        style="JST-XH",
        pincount=4,
        gender=Gender.FEMALE,
    )
    assert facet.gender is Gender.FEMALE


def test_supply_facet_has_the_designed_fields() -> None:
    """`SupplyFacet` carries `supplier`, `supplier_part_number`, `note` (design/facets.md)."""
    facet = SupplyFacet(
        id=Id(kind="facet.supply", value="5" * 32),
        key=("examples", "relay", "supply", "example-distributor"),
        subject=Id(kind="part", value="6" * 32),
        supplier="Example Distributor",
        supplier_part_number="EX-12345",
        note="",
    )
    assert facet.supplier == "Example Distributor"


def test_pcb_facet_has_the_designed_fields() -> None:
    """`PcbFacet` carries `revision`; marks a `Part` as a board (facets.md, connectivity.md)."""
    facet = PcbFacet(
        id=Id(kind="facet.pcb", value="7" * 32),
        key=("examples", "harness-board", "pcb"),
        subject=Id(kind="part", value="8" * 32),
        revision="B",
    )
    assert facet.revision == "B"


def test_footprint_facet_has_the_designed_fields() -> None:
    """`FootprintFacet` carries `library`, `name` (design/facets.md)."""
    facet = FootprintFacet(
        id=Id(kind="facet.footprint", value="9" * 32),
        key=("examples", "r1", "footprint"),
        subject=Id(kind="part", value="a" * 32),
        library="Resistor_SMD",
        name="R_0603_1608Metric",
    )
    assert facet.library == "Resistor_SMD"


def test_facet_subject_kind_is_enforced_at_freeze() -> None:
    """A `TerminalFacet` whose `subject` names a `part`, not an `item`, is a `FreezeError`."""
    wrong_kind_subject = Id(kind="part", value="b" * 32)
    facet = TerminalFacet(
        id=Id(kind="facet.terminal", value="c" * 32),
        key=("examples", "bad-subject", "terminal"),
        subject=wrong_kind_subject,
        group="L1",
        index=1,
    )
    with pytest.raises(FreezeError):
        _freeze((facet,))


def test_second_single_cardinality_facet_on_one_subject_is_a_freeze_error() -> None:
    """A second `TerminalFacet` on the same `Item` is a `FreezeError`, not a `Finding`.

    `unique=True` is a schema rule declared on `@record` (design/kernel-records.md 5.3), so
    `freeze()` enforces it and raises; the cardinality violation never reaches a validator.
    """
    first = TerminalFacet(
        id=Id(kind="facet.terminal", value="d" * 32),
        key=("examples", "shared-subject", "terminal-a"),
        subject=_SUBJECT,
        group="L1",
        index=1,
    )
    second = TerminalFacet(
        id=Id(kind="facet.terminal", value="e" * 32),
        key=("examples", "shared-subject", "terminal-b"),
        subject=_SUBJECT,
        group="L1",
        index=2,
    )
    with pytest.raises(FreezeError):
        _freeze((first, second))


def test_supply_allows_several_facets_on_one_part() -> None:
    """Two `SupplyFacet`s on the same `Part` freeze without error; `supply` is the exception."""
    part_subject = Id(kind="part", value="f" * 32)
    first = SupplyFacet(
        id=Id(kind="facet.supply", value="1" * 32),
        key=("examples", "relay", "supply", "distributor-a"),
        subject=part_subject,
        supplier="Distributor A",
        supplier_part_number="A-1",
        note="",
    )
    second = SupplyFacet(
        id=Id(kind="facet.supply", value="2" * 32),
        key=("examples", "relay", "supply", "distributor-b"),
        subject=part_subject,
        supplier="Distributor B",
        supplier_part_number="B-1",
        note="",
    )
    part = Part(
        id=part_subject,
        key=("examples", "relay"),
        mpn="EXAMPLE-RELAY-1",
        manufacturer="Example Co",
        description="Invented example relay for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    model = _freeze((part, first, second))
    assert model is not None
