"""The one path that writes a boundary's stated values: `Fn.limits` and `Terminal.limits` (TL1)."""

from typing import TYPE_CHECKING, Any

from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.vocab import Operating, Rating

    from .handles import Fn


def state_limits(
    owner: str,
    fn: Fn,
    scope: Any,  # noqa: ANN401 -- a unit `Scope` or the root design; neither can be imported here
    rating: Rating | None,
    operating: Operating | None,
) -> None:
    """Write `scope.boundary(fn, rating=, operating=)`; no value raises and writes nothing."""
    if rating is None and operating is None:
        msg = (
            f"{owner}.{fn.name}.limits states a rating or an operating value; "
            "to mark a boundary, use interface=True on the device"
        )
        raise AuthorError(msg)
    if rating is not None and (rating.breaking_ac or rating.breaking_dc):
        msg = f"{owner}.{fn.name}.limits: a boundary does not re-rate a breaking capacity"
        raise AuthorError(msg)
    scope = scope or fn._recorder  # the unit scope; the root design raises
    scope.boundary(fn, rating=rating, operating=operating)  # ty: ignore[unresolved-attribute] -- the recorder fallback is the root design, which has boundary
