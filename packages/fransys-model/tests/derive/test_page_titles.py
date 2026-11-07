"""PT3's short form and the title forms: the pure parts of the page title (PAGES-TITLES)."""

import pytest
from derive_helpers import frozen_with_library

from fransys_model.derive import page_title_forms, short_title
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.layout import DrawingSet, Page, PageGroup, PageRole
from fransys_model.vocab import Aspect, AspectNode

MODEL = frozen_with_library(Draft())


@pytest.mark.parametrize(
    ("entries", "short"),
    [
        (
            ("Relay and lamp circuit 1", "Relay and lamp circuit 2", "Relay and lamp circuit 3"),
            "Relay and lamp circuit 1 to 3",
        ),
        (
            ("Relay and lamp circuit 1", "Relay and lamp circuit 11"),
            "Relay and lamp circuit 1 to 11",
        ),
        (("Supply", "Mixer", "Pump 2"), "Supply to Pump 2"),
        (("-A1", "-B1", "-H1"), "-A1 to -H1"),
        (("Pump", "Pump 2"), "Pump to Pump 2"),
        (("Pump 1", "Pump"), "Pump 1 to Pump"),
        (("Pump 1",), None),
        (("Pump", "Pump"), None),
    ],
)
def test_the_short_form_prints_shared_leading_words_once(entries: tuple[str, ...], short: str | None) -> None:
    assert short_title(MODEL, entries) == short


def test_a_title_names_each_text_once_across_its_groups() -> None:
    nodes = tuple(
        AspectNode(id=make_id(AspectNode, ("n", label)), key=("n", label), aspect=Aspect.FUNCTION, parent=None, label=label, description="Pump 1")
        for label in ("A", "B")
    )
    drawing_set = DrawingSet(id=make_id(DrawingSet, ("s",)), key=("s",), location=None, unit=None, number=1, produced_by="test")
    page = Page(
        id=make_id(Page, ("p",)), key=("p",), drawing_set=drawing_set.id, number=1, role=PageRole.POWER, sheet_format=None,
        groups=tuple(PageGroup(group=node.id, index=i) for i, node in enumerate(nodes)), produced_by="test",
    )  # fmt: skip
    draft = Draft()
    draft.extend((*nodes, drawing_set, page), origin=Origin(file="t.py", line=1, note="fixture"))
    assert page_title_forms(frozen_with_library(draft), page) == ("Pump 1",)
