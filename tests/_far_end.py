"""Item and stub lookups for the far-end list field cases."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    import fransys as fr


def item_named(model: fr.Model, name: str) -> Any:
    return next(i for i, item in items(model).items() if item.key[-1] == name)


def stub_text(model: fr.Model, name: str, pin: str) -> str:
    """The off stub's text for the port `pin` of the item (or terminal of the strip) `name`."""
    port = next(p for p, rec in ports(model).items() if items(model)[functions(model)[rec.function].item].key[0] == name and rec.name == pin)
    return "".join(stub_far_end(model, port))
