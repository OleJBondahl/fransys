"""The PE ports each scope collects for `d.earth`; the draft gets the one `PE` net on hand-over."""

from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.vocab import Net

from ._earth_net import earth_net
from ._keys import scoped
from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey, Draft, Id, Origin
    from fransys_model.vocab import Port

_WITH_NET = (
    'd.detail.net("PE", ...) beside d.earth in one scope: d.earth is the scope\'s one PE net, '
    "so join every PE pin with d.earth"
)


class Earths:
    """Per scope, the ports of its `d.earth` calls, in call order and without repeats (model-0236).

    The scope's one `PE` net is built from them when the draft is given out (`nets`); a later
    call would be lost, so it raises.
    """

    def __init__(self) -> None:
        """Start with no scope."""
        self._ports: dict[AuthoringKey, dict[Id[Port], None]] = {}
        self._origin: dict[AuthoringKey, Origin] = {}
        self.closed = False

    def collect(
        self, prefix: AuthoringKey, ports: tuple[Id[Port], ...], origin: Origin, draft: Draft
    ) -> None:
        """Add `ports` to the scope `prefix`'s PE ports; raises once the draft was given out."""
        if self.closed:
            msg = (
                "d.earth came after the draft was read (fr.build or d.draft()): "
                "make every d.earth call first"
            )
            raise AuthorError(msg)
        if not self.has(prefix) and draft.record_of(make_id(Net, pe_key(prefix))) is not None:
            raise AuthorError(_WITH_NET)
        self._ports.setdefault(prefix, {}).update(dict.fromkeys(ports))
        self._origin.setdefault(prefix, origin)

    def refuse_net(self, prefix: AuthoringKey) -> None:
        """Raise when the scope `prefix` has `d.earth` calls and a `PE` net is declared too."""
        if self.has(prefix):
            raise AuthorError(_WITH_NET)

    def has(self, prefix: AuthoringKey) -> bool:
        """Whether the scope `prefix` has a `d.earth` call."""
        return prefix in self._ports

    def ports_of(self, prefix: AuthoringKey) -> tuple[Id[Port], ...]:
        """The PE ports collected so far for the scope `prefix`: the one read of them."""
        return tuple(self._ports.get(prefix, ()))

    def nets(self) -> list[tuple[Net, Origin]]:
        """The one `PE` net of each scope, with the origin of its first call; closes the set."""
        self.closed = True
        found = []
        for prefix in self._ports:
            net = earth_net(pe_key(prefix), self.ports_of(prefix))
            found.append((net, self._origin[prefix]))
        return found


def pe_key(prefix: AuthoringKey) -> AuthoringKey:
    """The authoring key of the scope `prefix`'s `PE` net."""
    return scoped(prefix, "net", "PE")
