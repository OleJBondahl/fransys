"""The refusal of a series element whose bridged run would tie different conductors together."""

from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError

if TYPE_CHECKING:
    from fransys_author.surface._ends import Parallel
    from fransys_author.surface._pairing import Ends

_TIED = 2  # two bridged members are enough to name


def _tied(element: object) -> bool:
    return bool(getattr(element, "_ties_terminals", False))


def _poles(width: int, before: Ends | None) -> str:
    marks = [end.mark for end in before.load] if before else []
    named = [mark.value for mark in marks if mark] if all(marks) and marks else []
    return ", ".join(named or [str(n) for n in range(1, width + 1)])


def _fix(tags: list[str]) -> str:
    taps = ", ".join(f"{tag[:-1]}, n, bridged=True)[1]" for tag in tags)
    more = ", ..." if len(tags) < _TIED else ""
    return (
        "Give each pole its own sized run and take one tap of each as a tuple, "
        f"one terminal per pole: ({taps}{more})"
    )


def refuse_tied_poles(parallel: Parallel, width: int, before: Ends | None) -> None:
    """Raise when bridged members of a parallel each take `width` poles and join them.

    Two bridged members meet each other's poles; one bridged member meets its own. Does not look
    at members that are not runs.
    """
    members: tuple[Any, ...] = parallel._members
    tied = [m for m in members if _tied(m)]
    if width < _TIED or not tied:
        return
    poles = _poles(width, before)
    if len(tied) == 1:
        raise AuthorError(_lone_text(tied[0]._tag, poles))
    first, second = (m._tag for m in tied[:_TIED])
    msg = (
        f"{first} and {second} both take poles {poles}: a bridged run ties its terminals, "
        f"so in a parallel the poles meet. {_fix([m._tag for m in tied])}"
    )
    raise AuthorError(msg)


def _lone_text(tag: str, poles: str) -> str:
    head = f"{tag} takes poles {poles}: a bridged run ties its terminals, so the poles meet."
    return f"{head} {_fix([tag])}"


def refuse_lone_tied_poles(element: object, width: int, before: Ends | None) -> None:
    """Raise when one bridged run takes `width` poles of a series and its bridge joins them."""
    if width < _TIED or not _tied(element):
        return
    run: Any = element
    raise AuthorError(_lone_text(run._tag, _poles(width, before)))
