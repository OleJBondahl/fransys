"""The part line each run's header carries (pdf-0021): `_part_line`, pure over a `HarnessCable`.

CT2-CT4's per-cable heading, "by others" note and core table are gone (pdf-0022): a cable block
carries them, drawn by `fransys_render`. The line stays, a bare `HarnessCable` built by hand.
"""

from decimal import Decimal

from _build import item, model, part
from fransys_pdf._drawings import _harness_block, _part_line

from fransys_model.derive import HarnessCable, HarnessCore, HarnessEnd


def _cable(  # noqa: PLR0913 -- one keyword per `HarnessCable` field under test, as `_build`'s own helpers do
    *,
    designation: str = "-W1",
    mpn: str | None = None,
    description: str | None = None,
    core_count: int | None = None,
    gauge_mm2: Decimal | None = None,
    length_mm: int | None = None,
    cores: tuple[HarnessCore, ...] = (),
    ends: tuple[HarnessEnd, ...] = (),
) -> HarnessCable:
    """A bare `HarnessCable`, `designation` real and every other field left to its keyword."""
    return HarnessCable(
        cable=item("cable-under-test", description="Cable one").id,
        designation=designation,
        mpn=mpn,
        description=description,
        core_count=core_count,
        gauge_mm2=gauge_mm2,
        shielded=None,
        length_mm=length_mm,
        cores=cores,
        ends=ends,
    )


# -- `_part_line` (pdf-0021) ------------------------------------------------------------------


def test_part_line_is_empty_when_every_field_is_none():
    """Every optional field unset: no text, no separators."""
    assert _part_line(_cable(designation="-W1")) == ""


def test_part_line_joins_mpn_description_and_the_composite():
    """The order is mpn, description, the core/gauge composite; the designation and the
    length are not part of it.
    """
    cable = _cable(
        designation="-W1",
        mpn="ACME-1",
        description="A cable",
        core_count=4,
        gauge_mm2=Decimal("1.5"),
        length_mm=1500,
    )
    assert _part_line(cable) == "ACME-1, A cable, 4 x 1.5 mm²"


def test_part_line_omits_the_composite_when_only_core_count_is_set():
    """`core_count` and `gauge_mm2` are one field: `gauge_mm2=None` drops the whole composite,
    proving it is not printed from `core_count` alone.
    """
    cable = _cable(designation="-W1", mpn="ACME-1", core_count=4, gauge_mm2=None)
    assert _part_line(cable) == "ACME-1"


def test_part_line_omits_the_composite_when_only_gauge_is_set():
    """The other half of the same proof: `core_count=None` alone also drops the composite."""
    cable = _cable(designation="-W1", mpn="ACME-1", core_count=None, gauge_mm2=Decimal("1.5"))
    assert _part_line(cable) == "ACME-1"


def test_part_line_omits_mpn_and_description_when_falsy():
    """`mpn=""` and `description=None` are both falsy and drop like `None`."""
    cable = _cable(designation="-W1", mpn="", description=None, core_count=2, gauge_mm2=Decimal(1))
    assert _part_line(cable) == "2 x 1 mm²"


def test_the_harness_block_and_the_lone_cable_write_one_part_line_shape() -> None:
    """One part, one line: the harness block's line is the lone cable's with no composite."""

    harness_part = part("hh", description="Invented harness")
    harness = item("harness1", description="Demo harness", part=harness_part.id)
    block = _harness_block(model(harness_part, harness), harness.id, "k")
    cable = _cable(mpn=harness_part.mpn, description=harness_part.description)
    assert block.line == _part_line(cable)
