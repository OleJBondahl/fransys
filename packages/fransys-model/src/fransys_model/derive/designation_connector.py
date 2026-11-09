"""The connector label and segment rules, split from `designation` (decision model-0071)."""

from typing import Any
lazy from collections.abc import Iterable

from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.instance_tag import dashed
from fransys_model.kernel import DIGEST_CACHE_SIZE, SchemaError, digest_cached
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.tables import facets_of, functions, port_templates, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port


def facet_on[F](model: Model, subject: Id[Any], facet_type: type[F]) -> F | None:
    """The facet of `facet_type` on `subject`, read from the cached `facets_by_subject`."""
    facets = facets_of(model, facet_type)
    for facet in build_indexes(model).facets_by_subject.get(subject, ()):
        if facet in facets:
            return facets[facet]
    return None


def connector_label(marking: str | None, name: str) -> str | None:
    """The label a connector function prints, `None` for none: the one home of that rule.

    `marking` is the `connector` facet's (or the part file's) `marking`, read like `Port.marking`:
    `None` means the function's own `name` is the label (`None` again for an empty name), and
    `""` means no label (a shell or an earth stud, whose pins print under the item). A function
    that is no connector has no label either: the caller does not ask. `_connector_label` here
    and the part lint call it after reading their own inputs.

    Args:
        marking: The connector facet's (or part file's) `marking`, or `None` for unset.
        name: The function's own name, the fallback label when `marking` is `None`.

    Returns:
        The label to print, or `None` for none.
    """
    if marking is None:
        return name or None
    return marking or None


def _connector_label(model: Model, function: Function) -> str:
    """The label `function` prints as a connector, `""` for none.

    A function that is no connector prints none; otherwise `connector_label` reads the facet's
    `marking` (`None` when there is no facet) and the function's name.
    """
    if not function_role(model, function.id).pin_group:
        return ""
    facet = None if function.template is None else facet_on(model, function.template, ConnectorFacet)
    return connector_label(None if facet is None else facet.marking, function.name) or ""


def prints_connector_label(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a connector that prints a label; `SchemaError` if it is not in `model`.

    False for a non-connector and for `marking=""` (a shell, an earth stud): it only adds its pins.
    `harness_cables` reads a housing end's connector facts from a function for which this is true.
    """
    record = functions(model).get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    return bool(_connector_label(model, record))


def connector_segments(labels: Iterable[str | None]) -> tuple[str, ...]:
    """The segment each function prints behind its item's designation, in order.

    `labels` holds the connector label of each function of one item: `""` or `None` for none
    (a function that is no connector, or a shell that says `marking=""`). A device prints its
    connectors as sub-parts (`-U2-X1:1`) when two or more of its functions have a label, so that
    two pins named alike never print one text: a labelled function then gives `-<label>`, an
    unlabelled one `""`. With no label, or one, every segment is `""` (`-J1:1`). This is the
    one place the rule is decided: `connector_segment` and the part lint both call it.

    Args:
        labels: Each function's connector label, in index order, `""` or `None` for none.

    Returns:
        Each function's printed segment, in the same order: `-<label>` or `""`.
    """
    given = tuple(labels)
    if sum(1 for label in given if label) <= 1:
        return ("",) * len(given)
    return tuple(dashed(label) if label else "" for label in given)


def connector_segment(model: Model, function: Id[Function]) -> str:
    """`function`'s segment behind its item's designation (`-X1`), or `""`; raises if unknown.

    The label is the `connector` facet's `marking` when set, else the function's name.
    The one place the connector form is decided; `connector_segments` decides whether it prints.
    """
    all_functions = functions(model)
    record = all_functions.get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    siblings = build_indexes(model).functions_by_item.get(record.item, ())
    labels = [_connector_label(model, all_functions[sibling]) for sibling in siblings]
    return connector_segments(labels)[siblings.index(function)]


@digest_cached(DIGEST_CACHE_SIZE)
def _named(model: Model) -> dict[Id[Port], tuple[Id[Function], str]]:
    """Each port whose template names a connector pin, with that connector's function on its item and the pin.

    Read like `facts/joins.py`: by the item and the template. A connector the item lacks yields none.
    """
    all_functions = functions(model)
    templates = port_templates(model)
    function_of = {(f.item, f.template): f.id for f in all_functions.values() if f.template is not None}
    found = {}
    for port in ports(model).values():
        template = None if port.template is None else templates.get(port.template)
        if template is None or template.connector is None or template.connector_pin is None:
            continue
        target = function_of.get((all_functions[port.function].item, template.connector))
        if target is not None:
            found[port.id] = (target, template.connector_pin)
    return found


def port_connector(model: Model, port: Id[Port]) -> tuple[Id[Function], str | None]:
    """The connector function `port` is a pin of, and the pin it names there (`None` when it names none).

    A port that names a connector (`connector = "j3.1"`, decision model-0448) sits at that function's
    pin; any other port sits on its own function. The one input of every printed prefix and count.
    """
    named = _named(model).get(port)
    return (ports(model)[port].function, None) if named is None else named


def pin_port(model: Model, function: Id[Function], pin: str) -> Id[Port] | None:
    """`function`'s own port called `pin`: the header port a port naming that pin is counted under."""
    held = build_indexes(model).ports_by_function.get(function, ())
    return next((port for port in held if ports(model)[port].name == pin), None)


def connector_ports(model: Model, connector: Id[Function]) -> tuple[Id[Port], ...]:
    """The ports at `connector`: its own, then each port that names a pin it has no port for."""
    own = build_indexes(model).ports_by_function.get(connector, ())
    named = (port for port, (function, pin) in _named(model).items() if function == connector and pin_port(model, connector, pin) is None)
    return (*own, *named)
