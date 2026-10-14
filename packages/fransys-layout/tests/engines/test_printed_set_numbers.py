"""`printed_set_numbers`: every set is kept with no document, and a document prints its set."""

from typing import TYPE_CHECKING

from fransys_el import OPTIONS
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read.printed import printed_set_numbers
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab import AspectNode, Document, DocumentPreset, documents

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_ORIGIN = Origin(file="tests/engines/test_printed_set_numbers.py", line=1, note="printed")
_C1 = make_id(AspectNode, ("c1",))


def test_a_model_with_no_document_filters_nothing() -> None:
    """Breaks if a model with no Document drops items."""
    model, laid = _cabinet(with_document=False)
    assert not documents(model)
    assert printed_set_numbers(laid) is None


def test_a_document_prints_its_location_set() -> None:
    """A document prints its location set, so the None case above is not absence-only."""
    model, laid = _cabinet(with_document=True)
    assert documents(model)
    top_set = next(
        s for s in layout_of(laid, DrawingSet).values() if s.location == _C1 and s.unit is None
    )
    assert printed_set_numbers(laid) == frozenset({top_set.number})


def _cabinet(*, with_document: bool) -> tuple[Model, Model]:
    """The frozen cabinet and its laid-out model, with one Document at +C1 when asked."""
    draft = build_cabinet()
    if with_document:
        key = ("cabinet", "document")
        draft.extend(
            (
                Document(
                    id=make_id(Document, key),
                    key=key,
                    preset=DocumentPreset.CABINET_SCHEMATIC,
                    location=_C1,
                    item=None,
                    add=(),
                    remove=(),
                    cover="# invented cabinet",
                    notes=None,
                ),
            ),
            origin=_ORIGIN,
        )
    model = freeze(draft)
    laid, _ = lay_out_schematic(model, OPTIONS)
    return model, laid
