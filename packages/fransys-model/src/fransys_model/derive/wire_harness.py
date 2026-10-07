"""The harness a WIRE conductor belongs to (HA2, model-0171).

Reached as `fransys_model.derive.wire_harness.<name>`, not re-exported from `derive/__init__.py`.
`Conductor.carrier` stays `None` for a wire; the plugs' harness is the one fact.
"""

from fransys_model.vocab.wire_harness import wire_harnesses
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item


def harness_of_wire(model: Model, conductor: Id[Conductor]) -> Id[Item] | None:
    """The one harness the ends of WIRE `conductor` sit under; `None` when none or two disagree."""
    found = wire_harnesses(model, conductor)
    return found[0] if len(found) == 1 else None
