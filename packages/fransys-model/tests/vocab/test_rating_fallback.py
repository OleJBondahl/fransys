"""Fallback: the voltage to earth stands only with no pair.

A 400 V supply with N: L1, L2, L3 at 230 V max and 0/120/240 degrees, N at 0 V. A phase
stands 230 V to earth. A function with a rail pair in some state checks at its pairs, even
"""

from plant import Plant
from rating_plant import AC_400, rated, supply
from test_rail_pairs import _GENERIC, _NO, _load, _Relay

from fransys_model.checks.ratings import check_ratings
from fransys_model.derive import rail_pairs
from fransys_model.kernel import make_id
from fransys_model.vocab import PartRatingFacet
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.templates import Part

_PROTECTION = (
    "prot",
    FunctionKind.PROTECTION,
    (("1", _GENERIC), ("2", _GENERIC)),
    (("1", "2"),),
)


def _supply_plant() -> Plant:
    """A plant with the 400 V supply `400V`."""
    plant = Plant()
    supply(plant, "ac", AC_400, name="400V")
    return plant


def test_a_load_between_a_no_contact_l1_and_n_is_checked_at_its_pair_not_to_earth() -> None:
    """(a) L1 behind a relay's NO contact, N declared on the other port, rated 230 V AC."""
    plant = _supply_plant()
    relay = _Relay(plant, "k1", (_NO,))
    load = _load(plant, ac="230")
    plant.net("L1", (relay.pins["no.13"],), potential="L1")
    plant.wire(relay.pins["no.14"], load.p0, key="w-p0")
    plant.net("N", (load.p1,), potential="N")
    model = plant.model()
    assert rail_pairs(model, load.function) == frozenset({("L1", "N")})
    assert check_ratings(model) == ()


def _pole(rating: str) -> Plant:
    """A protection function `prot` of item `f1` rated `rating` V AC, L1 on pin 1 only.

    Its switched link is conductive, so L1 reaches both ports: one rail, no pair.
    """
    plant = _supply_plant()
    guard = _Relay(plant, "f1", (_PROTECTION,))
    plant.add(
        PartRatingFacet(
            id=make_id(PartRatingFacet, ("f1",)),
            key=("f1",),
            subject=make_id(Part, ("part-f1",)),
            rating=rated(ac=rating),
        )
    )
    plant.net("L1", (guard.pins["prot.1"],), potential="L1")
    assert rail_pairs(plant.model(), guard.functions["prot"]) == frozenset()
    return plant


def test_a_single_pole_in_one_conductor_rated_below_its_rail_to_earth_gives_the_finding() -> None:
    """(b) Phase L1 stands 230 V to earth: 200 V fires, and says so."""
    (finding,) = check_ratings(_pole("200").model())
    assert finding.subjects == (Plant.function_id("f1", "prot"),)
    assert finding.message == (
        f"function {ref(Plant.function_id('f1', 'prot'))} is rated 200 V AC (part or template rating), but rail 'L1' is at 230 V to earth"
    )


def test_the_same_single_pole_rated_above_its_rail_to_earth_gives_none() -> None:
    assert check_ratings(_pole("231").model()) == ()
