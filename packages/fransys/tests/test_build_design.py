"""EA1: `fr.build(d)` takes a surface `Design`, standing for its parts library and its circuit."""

import fransys as fr

from fransys_model.vocab import Item


def _design() -> fr.Design:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Demo cabinet")
    d.device("Q1", "DEMO-MCB-C6")
    return d


def _tags(result: fr.BuildResult) -> list[str | None]:
    return [r.tag for r in result.model.tables["item"].values() if isinstance(r, Item)]


def test_build_of_a_design_equals_build_of_its_library_and_draft() -> None:
    d = _design()
    assert fr.build(d).model.digest == fr.build(d.library, d.draft()).model.digest


def test_build_of_a_design_holds_its_devices() -> None:
    assert _tags(fr.build(_design())) == ["Q1"]


def test_a_design_mixes_with_plain_drafts() -> None:
    d = _design()
    plain = fr.build(d.library, d.draft(), fr.Draft())
    assert fr.build(d, fr.Draft()).model.digest == plain.model.digest
