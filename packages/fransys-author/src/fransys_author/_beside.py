"""The `beside=` check of `d.layout.chain`: a chain's end nets are two nets of its host."""

from typing import TYPE_CHECKING, Any

from fransys_model.vocab import Conductor

from .errors import AuthorError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Record

    from .handles import Fn


_ENDS = 2  # a chain leaves its host by two nets
type _PortId = Id[Any]
type _Nets = dict[_PortId, frozenset[_PortId]]


def check_beside(records: Iterable[Record], steps: list[Fn], host: Fn) -> None:
    """Raise `AuthorError` unless the chain's two end nets are two nets of `host`'s wired ports."""
    nets = _nets(records)
    ends = _end_nets(steps, nets)
    host_nets = {nets[port.id] for port in host.ports if port.id in nets}
    if len(ends) != _ENDS or not ends <= host_nets:
        msg = (
            f"d.layout.chain beside={'/'.join(host.key)}: the chain's end nets "
            f"{_names(ends, [*steps, host])} are not two nets of that function "
            f"({_names(host_nets, [*steps, host])}); wire first, then advise the chain"
        )
        raise AuthorError(msg)


def _nets(records: Iterable[Record]) -> _Nets:
    """Each wired port's net: the set of ports its conductors join."""
    joined: dict[_PortId, set[_PortId]] = {}
    for record in records:
        if isinstance(record, Conductor):
            both = joined.setdefault(record.a, {record.a}) | joined.setdefault(record.b, {record.b})
            for port in both:
                joined[port] = both
    return {port: frozenset(found) for port, found in joined.items()}


def _wired(fn: Fn, nets: _Nets) -> set[frozenset[_PortId]]:
    return {nets[port.id] for port in fn.ports if port.id in nets}


def _end_nets(steps: list[Fn], nets: _Nets) -> set[frozenset[_PortId]]:
    """The net each end of the chain leaves by: its end function's net the next one lacks."""
    if len(steps) == 1:
        return _wired(steps[0], nets)
    first = _wired(steps[0], nets) - _wired(steps[1], nets)
    last = _wired(steps[-1], nets) - _wired(steps[-2], nets)
    return first | last if len(first) == len(last) == 1 else set()


def _names(found: set[frozenset[_PortId]], fns: list[Fn]) -> str:
    """Each net by the keys of its ports on the given functions, sorted."""
    keys = {port.id: "/".join(port.key) for fn in fns for port in fn.ports}
    names = sorted(
        "(" + ", ".join(sorted(keys[p] for p in net if p in keys)) + ")" for net in found
    )
    return " ".join(names) if names else "(none: no wire reaches them)"
