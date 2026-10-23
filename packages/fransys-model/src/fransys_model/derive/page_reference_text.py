"""The text a page is named by wherever it is printed, one function (render-0018).

The set is `set_rank`, its place among its own unit's sets, so a reference names the page the
engineer finds in the PDF he holds (render-0015 amended).
"""

from fransys_model.layout import DrawingSet, Page, layout_of
lazy from fransys_model.kernel import Model

from .frame_position import location_path, position_text
from .house_settings import reference_text_of
from .set_rank import set_rank

__all__ = ["page_reference_text"]


def page_reference_text(model: Model, page: Page, *, with_location: bool = False) -> str:
    """`p3`, `p2.3` for page 3 of the unit's second set; `+CAB p3` with the set's location path."""
    labels: tuple[str, ...] = ()
    if with_location:
        node = layout_of(model, DrawingSet)[page.drawing_set].location
        labels = tuple(label for _, label in location_path(model, node))
    refs = reference_text_of(model)
    return position_text(refs, page.number, None, labels, set_number=set_rank(model, page))
