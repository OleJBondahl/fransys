"""The `layout.link_marker` of a core layout's lone marker, a stub or a copy (CORE-TEXTS C).

A lone marker has no partner on another page. It is an off stub: its own partner, its `far` and
`carrier` from `derive.stub_far`, its text the off-stub text of `derive.marker_text`.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import mate_ports, stub_far
from fransys_model.kernel import make_id
from fransys_model.layout import LinkMarker, MarkerSide, StarKind

from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import AuthoringKey, Id, Model
    from fransys_model.layout import Page, Side
    from fransys_model.vocab import Item, Port

__all__ = ["far_port", "off_stub", "stub_ends"]


def stub_ends(
    model: Model, ports: Sequence[Id[Port]]
) -> tuple[Id[Port], Id[Port], Id[Item] | None] | None:
    """`derive.stub_far` of the pin, else of the pin its mate joins: the line through the mate.

    A mated half no conductor leaves names the far end of its partner's conductor, and the half
    that end is mated to when it is (R467 Q02).
    """
    found = stub_far(model, ports)
    if found is not None:
        return found
    pairs = mate_ports(model)
    for here, there in (*pairs, *((b, a) for a, b in pairs)):
        via = stub_far(model, [there]) if here in ports else None
        if via is not None:
            beyond = next((b for a, b in pairs if a == via[1]), None)
            beyond = beyond or next((a for a, b in pairs if b == via[1]), via[1])
            return here, beyond, via[2]
    return None


def far_port(model: Model, ports: Sequence[Id[Port]]) -> tuple[Id[Port], Id[Port], Id[Item] | None]:
    """`(near, far, carrier)` of the stub the `ports` one pin draws (`stub_ends`).

    No conductor at the pin, its function or its mate is refused.
    """
    found = stub_ends(model, ports)
    if found is None:
        refuse(
            f"stub at ports {list(ports)}",
            "no conductor leaves its pin, its function or its mate, so its far end is unknown",
        )
    return found


def off_stub(  # noqa: PLR0913 - the record joins its key, page, ends, place, facing and stamp
    key: AuthoringKey,
    page: Page,
    ends: tuple[Id[Port], Id[Port], Id[Item] | None],
    at: tuple[int, int, int, int],
    facing: Side,
    *,
    stamp: str,
) -> LinkMarker:
    """One off stub at `ends[0]` naming `ends[1]` over `ends[2]`; `at` is x, y, width, height."""
    ident = make_id(LinkMarker, key)
    return LinkMarker(
        id=ident,
        key=key,
        page=page.id,
        port=ends[0],
        side=MarkerSide.OWNER,
        partner=ident,
        x=at[0],
        y=at[1],
        width=at[2],
        height=at[3],
        produced_by=stamp,
        star=StarKind.OFF,
        far=ends[1],
        carrier=ends[2],
        facing=facing,
    )
