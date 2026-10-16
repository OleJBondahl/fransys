"""STRIP_WITHOUT_TAG: a part-less top-level item that nothing can designate is an ERROR."""

from plant import Plant

from fransys_model.checks import check_strip_without_tag
from fransys_model.kernel import make_id
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.finding_ref import ref


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


def test_a_strip_whose_terminals_disagree_names_the_codes() -> None:
    plant = Plant()
    _strip(plant, "mixed", "X", "Y")
    (finding,) = check_strip_without_tag(plant.model())
    assert ref(finding.subjects[0]) in finding.message
    assert "mixed" not in finding.message
    assert "(X, Y)" in finding.message
