"""Template facts over a part: poles, sides, throws, contact kind and channel signal.

Decision model-0321 (EL-5). One function per rule, over plain templates so the author, whose
library is a `Draft`, calls the same code as the model. The rules sit in `part_poles` and
`part_throws`, re-exported here.
"""

lazy from collections.abc import Mapping

from fransys_model.derive.facts.part_pins import template_throws
from fransys_model.derive.facts.part_poles import (
    conductor_of,
    pin_side,
    pole_count,
    pole_pin_names,
    poles_of_template,
    unlinked_poles,
)
from fransys_model.derive.facts.part_throws import (
    THROW_WORDS,
    contact_kind_of,
    implied_rest,
    is_contact_kind,
)
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.enums import SignalType
lazy from fransys_model.vocab.facets import PlcChannelFacet
lazy from fransys_model.vocab.templates import FunctionTemplate

__all__ = [
    "THROW_WORDS",
    "channel_signal",
    "conductor_of",
    "contact_kind_of",
    "implied_rest",
    "is_contact_kind",
    "pin_side",
    "pole_count",
    "pole_pin_names",
    "poles_of_template",
    "template_throws",
    "unlinked_poles",
]


def channel_signal(template: Id[FunctionTemplate], channels: Mapping[Id[FunctionTemplate] | None, PlcChannelFacet]) -> SignalType | None:
    """The signal type of the PLC channel function template `template`, `None` if it is none.

    `channels` is `plc_channel_facets(model)`, or a library's facets keyed by their subject.
    """
    facet = channels.get(template)
    return None if facet is None else facet.signal
