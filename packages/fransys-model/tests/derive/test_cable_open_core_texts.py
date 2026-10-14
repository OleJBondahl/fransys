"""Open cores and core pairs: the rows and every printed text (CC6, CC7, CC10, CC11)."""

from decimal import Decimal

from plant import Plant
from query_builders import make_part, make_strip

from fransys_model.derive import cable_list_rows, open_core_rows, terminal_rows
from fransys_model.derive.cable_drawing import cable_heading
from fransys_model.derive.core_pairs import (
    core_mark,
    cores_text,
    drawn_pairs,
)
from fransys_model.derive.harness import top_level_cables
from fransys_model.derive.open_core_ends import open_core_text
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import (
    CableFacet,
    CableProductFacet,
    CorePair,
    OpenCoreFacet,
)

_COLOURS = ("WH", "BN", "WH", "BN", "SH", "SH")
_PAIRS = (CorePair(cores=(1, 2), screen=5), CorePair(cores=(3, 4), screen=6))


def _plant(
    pairs: tuple[CorePair, ...] = _PAIRS,
    *,
    plant: Plant | None = None,
    open_at: Id[Port] | None = None,
) -> tuple[Plant, Id[Item]]:
    """Cable W1 of a 2x2 product; cores 3 and 5 open (3 at `open_at`), the rest unwired."""
    plant = plant or Plant()
    part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cab", "product")),
            key=("cab", "product"),
            subject=part,
            core_colours=_COLOURS,
            gauge_mm2=Decimal("0.75"),
            shielded=False,
            pairs=pairs,
        )
    )
    cable = plant.item("w1", designation="W1", part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "c")), key=("w1", "c"), subject=cable, length_mm=25000
        )
    )
    for index, at in ((3, open_at), (5, None)):
        key = ("w1", "open", str(index))
        plant.add(
            OpenCoreFacet(
                id=make_id(OpenCoreFacet, key), key=key, subject=cable, index=index, at=at
            )
        )
    return plant, cable


def _heading(model: Model) -> str:
    (cable,) = top_level_cables(model)
    return cable_heading(model, cable, None)


def test_open_core_rows_carry_colour_landing_and_spare() -> None:
    # MUTATION: `spare` is true for an SH core
    plant, cable = _plant()
    spare, screen = open_core_rows(plant.model(), cable)
    assert (spare.index, spare.colour, spare.spare, spare.at_designation) == (3, "WH", True, "")
    assert (screen.index, screen.colour, screen.spare) == (5, "SH", False)


def test_open_core_text_says_spare_for_a_core_and_screen_for_a_screen() -> None:
    # MUTATION: `open_core_text` leaves the word `spare` out
    plant, cable = _plant()
    model = plant.model()
    spare, screen = open_core_rows(model, cable)
    pairs = drawn_pairs(model, cable)
    assert open_core_text(spare, core_mark(pairs, 3)) == "3 WH spare"
    assert open_core_text(screen, core_mark(pairs, 5)) == "5 SH screen P1"


def test_a_pair_mark_prints_only_off_a_bracket() -> None:
    plant, cable = _plant(
        (CorePair(cores=(1, 3), screen=None), CorePair(cores=(2, 4), screen=None))
    )
    pairs = drawn_pairs(plant.model(), cable)
    assert [pair.bracket for pair in pairs] == [False, False]
    assert [core_mark(pairs, n) for n in (1, 2, 3, 4)] == ["P1", "P2", "P1", "P2"]
    assert core_mark(drawn_pairs(_plant()[0].model(), cable), 1) == ""


def test_the_heading_names_pairs_and_screened_pairs() -> None:
    # MUTATION: `screened_pairs` is true whenever there are pairs
    assert _heading(_plant()[0].model()) == "-W1, 2x2x0.75, screened pairs, 25000 mm"
    half = (CorePair(cores=(1, 2), screen=5), CorePair(cores=(3, 4), screen=None))
    assert _heading(_plant(half)[0].model()) == "-W1, 2x2x0.75, 25000 mm"
    assert _heading(_plant(())[0].model()) == "-W1, 25000 mm"


def test_the_cable_list_gives_pairs_and_a_pair_cores_cell() -> None:
    # MUTATION: `cable_list_rows` leaves `pairs` as None
    (row,) = cable_list_rows(_plant()[0].model())
    assert row.pairs == 2
    assert cores_text(row.core_count, row.pairs) == "2x2"
    (plain,) = cable_list_rows(_plant(())[0].model())
    assert plain.pairs is None
    assert cores_text(plain.core_count, plain.pairs) == str(plain.core_count)


def test_a_terminal_lists_the_open_core_that_lands_on_it() -> None:
    # MUTATION: `terminal_rows` leaves out `open_ends_at`
    plant = Plant()
    strip, (_, _, n1) = make_strip(plant)
    plant, _ = _plant(plant=plant, open_at=n1.external)
    rows = terminal_rows(plant.model(), strip)
    (row,) = [r for r in rows if "-W1 WH spare" in r.external_ends]
    assert row.terminal == make_id(Item, ("x1", "t-n1"))
