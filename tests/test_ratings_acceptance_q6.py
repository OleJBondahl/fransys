"""RATINGS-1 step 3, acceptance for Q6: read a part's values from the catalogue (parts-0006).

Two demo parts carry the data: `DEMO-TBLK-2P-DUAL` (template rating 250 V AC, part rating 500 V AC
and 400 V DC) and `DEMO-CELL-3V6` (an operating envelope with `min_voltage_v = "0"`). B4: the
function read is the template's whole record, else the part's. B5: a unit authors its boundary
values from `s.operating`. B7: the cell's zero minimum loads and reads back as `Decimal("0")`.

Can-fail probes, each one Edit, run and undone: deleting the template's `[function.rating]` table
in the tracked demo part fails B4's template test; making the catalogue read no `OperatingFacet`
fails B5 and B7.
"""

from decimal import Decimal
from pathlib import Path

import fransys_parts
from fransys_author import Design

from fransys_model.kernel import freeze, merge
from fransys_model.vocab import BoundaryValuesFacet, function_rating, part_rating
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.tables import boundaries, facets_of, parts

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo-parts" / "demo_parts"
TBLK = "DEMO-TBLK-2P-DUAL"
CELL = "DEMO-CELL-3V6"
_TEMPLATE_TABLE = '\n[function.rating]\nvoltage_ac_v = "250"\n'
_PART_RATING = Rating(voltage_ac_v=Decimal(500), voltage_dc_v=Decimal(400))


def _demo_design() -> Design:
    return Design(fransys_parts.load("demo_parts"))


def _library_without_template_rating(tmp_path: Path) -> Path:
    """A library of the terminal part alone, its `[function.rating]` table deleted."""
    text = (DEMO / "parts" / "terminal-dual-rated-2p.toml").read_text()
    assert _TEMPLATE_TABLE in text
    root = tmp_path / "lib"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text((DEMO / "library.toml").read_text())
    (root / "parts" / "terminal-dual-rated-2p.toml").write_text(text.replace(_TEMPLATE_TABLE, ""))
    return root


# -- B4: the function's rating is the template's, else the part's, as a whole record --------------


def test_the_templates_rating_is_the_function_rating() -> None:
    d = _demo_design()
    assert d.rating(TBLK, "terminal") == Rating(voltage_ac_v=Decimal(250))


def test_the_part_rating_holds_both_the_ac_and_the_dc_value() -> None:
    assert _demo_design().rating(TBLK) == _PART_RATING


def test_a_template_rating_with_only_ac_hides_the_parts_dc_value() -> None:
    read = _demo_design().rating(TBLK, "terminal")
    assert read is not None
    assert read.voltage_dc_v is None
    assert read.voltage_ac_v == Decimal(250)


def test_the_built_models_function_and_part_readers_agree_with_the_catalogue() -> None:
    d = _demo_design()
    x1 = d.item(TBLK, name="x1")
    model = freeze(merge(fransys_parts.load("demo_parts"), d.draft()))
    part = next(p for p in parts(model).values() if p.mpn == TBLK)
    assert function_rating(model, x1.fn("terminal").id) == d.rating(TBLK, "terminal")
    assert part_rating(model, part.id) == d.rating(TBLK) == _PART_RATING


def test_without_a_template_rating_the_function_falls_back_to_the_parts_whole_rating(
    tmp_path: Path,
) -> None:
    d = Design(fransys_parts.load_path(_library_without_template_rating(tmp_path)))
    assert d.rating(TBLK, "terminal") == _PART_RATING
    assert d.rating(TBLK, "terminal") == d.rating(TBLK)


# -- B5: a unit authors its boundary values from the catalogue ------------------------------------


def test_a_unit_states_twice_the_cells_operating_values_on_its_boundary() -> None:
    d = _demo_design()
    cell = d.operating(CELL, "cell")
    assert cell is not None
    assert cell.nominal_voltage_v is not None
    u = d.scope("pack").unit("pack", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    x1 = u.item("DEMO-CONN-2P", name="x1")
    u.boundary(
        x1,
        operating=Operating(
            nominal_voltage_v=2 * cell.nominal_voltage_v, capacity_ah=cell.capacity_ah
        ),
    )
    model = freeze(merge(fransys_parts.load("demo_parts"), d.draft()))
    (facet,) = facets_of(model, BoundaryValuesFacet).values()
    (boundary,) = boundaries(model).values()
    assert facet.subject == boundary.id
    assert facet.operating == Operating(nominal_voltage_v=Decimal("7.2"), capacity_ah=Decimal(3))
    assert facet.rating is None


# -- B7: a zero minimum is a value, not an absent one --------------------------------------------


def test_the_demo_cells_zero_minimum_loads_and_reads_back_as_decimal_zero() -> None:
    cell = _demo_design().operating(CELL, "cell")
    assert cell == Operating(
        nominal_voltage_v=Decimal("3.6"),
        max_voltage_v=Decimal("4.2"),
        min_voltage_v=Decimal(0),
        capacity_ah=Decimal(3),
    )
    assert cell is not None
    assert cell.min_voltage_v is not None
    assert cell.min_voltage_v == Decimal(0)


def test_the_cell_has_no_rating_of_its_own() -> None:
    d = _demo_design()
    assert d.rating(CELL) is None
    assert d.rating(CELL, "cell") is None
