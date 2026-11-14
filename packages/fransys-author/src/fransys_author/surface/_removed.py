"""`refuse`: the error for a missing attribute of `fr`, Design, Detail, Layout, Fn or Terminal."""

from typing import NoReturn

from fransys_author.errors import AuthorAttributeError


def refuse(owner: str, name: str) -> NoReturn:
    """Raise the AuthorAttributeError for a missing attribute `name` of `owner`.

    Private names (`_x`) raise it too, so copy and pickle probes see an AttributeError.
    Does not return: it always raises.
    """
    msg = f"{owner!r} has no attribute {name!r}"
    raise AuthorAttributeError(msg)
