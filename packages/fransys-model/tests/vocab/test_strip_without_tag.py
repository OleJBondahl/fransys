"""STRIP_WITHOUT_TAG: a part-less top-level item that nothing can designate is an ERROR."""

from plant import Plant

from fransys_model.kernel import Severity, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.validators import ALL_VALIDATORS, check_strip_without_tag
from fransys_model.vocab.validators.strip_without_tag import STRIP_WITHOUT_TAG


def _strip(plant: Plant, key: str, *codes: str, tag: str | None = None) -> None:
    """A part-less strip `key` with one terminal per class code in `codes`."""
    strip = plant.item(key, designation=tag)
    for n, code in enumerate(codes, 1):
        term = plant.item(f"{key}-t{n}", parent=strip, part=plant.part(code))
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (key, str(n))),
                key=(key, str(n)),
                subject=term,
                group="",
                index=n,
            )
        )


def test_the_check_is_registered() -> None:
    assert check_strip_without_tag in ALL_VALIDATORS


def test_a_strip_with_no_terminals_is_an_error_naming_its_key() -> None:
    plant = Plant()
    _strip(plant, "empty")
    (finding,) = check_strip_without_tag(plant.model())
    assert (finding.code, finding.severity) == (STRIP_WITHOUT_TAG, Severity.ERROR)
    assert finding.subjects == (make_id(Item, ("empty",)),)
    assert "empty" in finding.message
    assert "no terminals" in finding.message


def test_a_strip_whose_terminals_disagree_names_the_codes() -> None:
    plant = Plant()
    _strip(plant, "mixed", "X", "Y")
    (finding,) = check_strip_without_tag(plant.model())
    assert "mixed" in finding.message
    assert "(X, Y)" in finding.message


def test_a_strip_that_can_be_designated_is_silent() -> None:
    plant = Plant()
    _strip(plant, "agreed", "X", "X")
    _strip(plant, "tagged", tag="X9")
    plant.item("device", part=plant.part("K"))
    assert check_strip_without_tag(plant.model()) == ()
