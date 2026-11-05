"""The conductors of a design as the ends they join, for the series and pair field cases."""

from typing import TYPE_CHECKING, Any

import fransys as fr

from fransys_model.vocab.tables import conductors, functions, ports

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port


def pin_name(key: tuple[str, ...]) -> tuple[str, str]:
    """The item and pin of a port key; a terminal's pin is its number."""
    return key[0], key[2] if "terminal" in key else key[-1]


def ends_of(d: fr.Design, name: Callable[[tuple[str, ...]], tuple[str, ...]]) -> set[frozenset[tuple[str, ...]]]:
    """Every conductor as the two ends `name` makes of its port keys."""
    model = fr.build(d).model
    conductors_: list[Any] = list(model.tables["conductor"].values())
    return {frozenset(name(model.key_of(p) or ()) for p in (c.a, c.b)) for c in conductors_}


def cores(model: Model, cable: str) -> dict[str, frozenset[str]]:
    """Core number -> the two ends as `X8:1` or `B1:2`."""
    fns = functions(model)

    def end(port_id: Id[Port]) -> str:
        port = ports(model)[port_id]
        key = fns[port.function].key
        return f"{key[0]}:{key[2] if key[1] == 'terminal' else port.name}"

    return {c.key[-1]: frozenset({end(c.a), end(c.b)}) for c in conductors(model).values() if c.key[0] == cable}
