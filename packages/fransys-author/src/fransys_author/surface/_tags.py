"""The bare-tag rule: a call gives the aspect's prefix, the author never writes it."""

from fransys_author.errors import AuthorError
from fransys_model.vocab import DESIGNATION_SCHEME, Aspect

_ASPECT = {
    "device": Aspect.PRODUCT,
    "terminal_strip": Aspect.PRODUCT,
    "cable": Aspect.PRODUCT,
    "harness": Aspect.PRODUCT,
    "rack": Aspect.PRODUCT,
    "add": Aspect.PRODUCT,
    "location": Aspect.LOCATION,
    "function": Aspect.FUNCTION,
}


def bare(tag: str, call: str) -> str:
    """`tag` unchanged; one that starts with `-`, `+` or `=` raises, naming `call`'s own prefix."""
    if not tag or tag[0] in DESIGNATION_SCHEME.sign_characters():
        sign = DESIGNATION_SCHEME.sign(_ASPECT[call])
        msg = f"write {tag[1:] or '<tag>'}; {call}() adds the {sign}"
        raise AuthorError(msg)
    return tag


def floating_name(tag: str | None, name: str | None, call: str) -> str | None:
    """`name`, after `tag` passes `bare`; a call with neither a tag nor `name=` raises."""
    if tag is not None:
        bare(tag, call)
    elif name is None:
        msg = f"give a tag, or name= for a {call.replace('_', ' ')} with no tag"
        raise AuthorError(msg)
    return name
