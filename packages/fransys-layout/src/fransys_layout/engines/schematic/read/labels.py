"""The text of every first-pass label, read from the model (layout-0027), and the requests.

A request also needs the chosen symbol (its slot names), which only `resolve` knows, so
`label_requests` builds the requests after `resolve` from the texts `label_texts` read.
"""

from typing import TYPE_CHECKING, Any
lazy from collections.abc import Set as AbstractSet

from fransys_layout.stages import LabelKind, LabelRequest
from fransys_model.derive.drawing_text import port_marking, tag_text
from fransys_model.kernel import Id, value
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_layout.stages import DrawnFunction
    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function


@value
class LabelText:
    """The text of one label to be; `subject` is a function, a model port or a conductor."""

    kind: LabelKind
    subject: Id[Any]
    text: str


def label_texts(
    model: Model, indexes: Indexes, drawn: AbstractSet[Id[Function]]
) -> tuple[LabelText, ...]:
    """A `TAG` text per drawn function, a `MARKING` text per its ports, a `WIRE` text per label."""
    texts: list[LabelText] = []
    for function in functions(model).values():
        if function.id not in drawn:
            continue
        function_ports = indexes.ports_by_function.get(function.id, ())
        tag = tag_text(model, function.id)
        texts.append(LabelText(kind=LabelKind.TAG, subject=function.id, text=tag))
        texts.extend(
            LabelText(kind=LabelKind.MARKING, subject=port_id, text=port_marking(model, port_id))
            for port_id in function_ports
        )
    return tuple(sorted(texts, key=lambda text: (text.kind.value, text.subject)))


def label_requests(
    texts: tuple[LabelText, ...], drawn: tuple[DrawnFunction, ...]
) -> tuple[LabelRequest, ...]:
    """Every first-pass `LabelRequest` with its final slot; the engine calls it after `resolve`."""
    text_of = {(text.kind, text.subject): text.text for text in texts}
    requests: list[LabelRequest] = []
    for function in drawn:
        slots = {slot.slot for slot in function.geometry.slots}
        if "tag" in slots:
            requests.append(
                LabelRequest(
                    kind=LabelKind.TAG,
                    subject=function.function,
                    slot="tag",
                    text=text_of[LabelKind.TAG, function.function],
                )
            )
        for port in function.ports:
            slot = f"marking.{port.symbol_port}"
            # I4 R1: a port whose part prints no marking gets no marking label
            if slot in slots and text_of[LabelKind.MARKING, port.port]:
                requests.append(
                    LabelRequest(
                        kind=LabelKind.MARKING,
                        subject=port.port,
                        slot=slot,
                        text=text_of[LabelKind.MARKING, port.port],
                    )
                )
    return tuple(sorted(requests, key=lambda r: (r.kind.value, r.subject, r.slot)))
