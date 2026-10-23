"""The `beside=` check of `d.layout.chain`: a chain joins its host by one or two end nets."""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import physical_nets

from ._draft_view import draft_view
from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id

    from .handles import Fn


_ENDS = 2  # a chain leaves its host by one or two nets
type _PortId = Id[Any]
type _Net = frozenset[_PortId]
type _Nets = dict[_PortId, _Net]


def check_beside(draft: Draft, steps: list[Fn], host: Fn) -> None:
    """Raise `AuthorError` unless a chain end net is a net of `host`'s wired ports (one or two)."""
    nets = _nets(draft)
    first, last = _end_nets(steps, nets)
    host_nets = _wired(host, nets)
    why = _fault(len(steps), first, last, host_nets)
    if why:
        msg = (
            f"d.layout.chain beside={'/'.join(host.key)}: {why}; the chain's end nets "
            f"{_names(first | last, [*steps, host])} against the nets of that function "
            f"({_names(host_nets, [*steps, host])}). A chain joins its host by one or two "
            "end nets, at least one a net of that function; wire first, then advise the chain"
        )
        raise AuthorError(msg)


def _fault(count: int, first: set[_Net], last: set[_Net], host_nets: set[_Net]) -> str:
    """Why the chain cannot stand beside the host, or an empty string."""
    ends = first | last
    if count > 1 and max(len(first), len(last)) > 1:
        return "an end function has two or more nets its neighbour lacks"
    if len(ends) > _ENDS:
        return f"the chain leaves by {len(ends)} nets"
    if not ends & host_nets:
        return "no end net is a net of that function"
    if count > 1 and first == last:
        return "both end nets are the same net, so the chain is a loop on one net"
    return ""


def _nets(draft: Draft) -> _Nets:
    """Each wired port's net: its physical net when that joins two or more ports."""
    joined = physical_nets(draft_view(draft))
    return {
        port: frozenset(net.ports) for net in joined if len(net.ports) > 1 for port in net.ports
    }


def _wired(fn: Fn, nets: _Nets) -> set[_Net]:
    return {nets[port.id] for port in fn.ports if port.id in nets}


def _end_nets(steps: list[Fn], nets: _Nets) -> tuple[set[_Net], set[_Net]]:
    """The nets each end of the chain leaves by: its end function's nets the next one lacks.

    An end with none of its own (a one-pin box) only closes the chain. A one-step chain leaves by
    all its wired nets, counted as its first end.
    """
    if len(steps) == 1:
        return _wired(steps[0], nets), set()
    first = _wired(steps[0], nets) - _wired(steps[1], nets)
    last = _wired(steps[-1], nets) - _wired(steps[-2], nets)
    return first, last


def _names(found: set[_Net], fns: list[Fn]) -> str:
    """Each net by the keys of its ports on the given functions, sorted."""
    keys = {port.id: "/".join(port.key) for fn in fns for port in fn.ports}
    names = sorted(
        "(" + ", ".join(sorted(keys[p] for p in net if p in keys)) + ")" for net in found
    )
    return " ".join(names) if names else "(none: no wire reaches them)"
