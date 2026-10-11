"""Shared builders for the changeover-contact tests: an invented changeover relay part.

`test_changeover_throws` and `test_link_state` both build one part whose contact functions have
ports with a `PortTemplate.role`, then instantiate it on one or more items. Names keep their
leading underscore, as the sibling test modules that share builders do.
"""

from derive_helpers import add_all
from examples import bundle_records

from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab.core import Function, Port
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.templates import InternalLink

_PART_KEY = ("cs2", "relay")
_ITEM_KEY = ("cs2", "k1")
_ROLES = (PortRole.COMMON, PortRole.BREAK, PortRole.MAKE)
_NUMBERED = ("11", "12", "14")


def _model(bundle: PartBundle, origin: Origin, *item_keys: tuple[str, ...]) -> Model:
    """A frozen model holding `bundle` and one item per key in `item_keys` (default one)."""
    draft = Draft()
    add_all(draft, *bundle_records(bundle), origin=origin)
    for key in item_keys or (_ITEM_KEY,):
        add_all(draft, *instantiate(bundle, key), origin=origin)
    return freeze(draft)


def _function(number: int, item_key: tuple[str, ...] = _ITEM_KEY) -> Id[Function]:
    return make_id(Function, (*item_key, "fn", f"co_{number}"))


def _port(number: int, name: str, item_key: tuple[str, ...] = _ITEM_KEY) -> Id[Port]:
    return make_id(Port, (*item_key, "fn", f"co_{number}", "port", name))


def _link(number: int, other: str) -> Id[InternalLink]:
    """The template link of function `co_<number>` that joins its first port to port `other`."""
    return make_id(InternalLink, (*_PART_KEY, "fn", f"co_{number}", "link", other))
