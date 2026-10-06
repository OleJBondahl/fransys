"""The bare-tag rule (EA2): a call gives the aspect's prefix, the author never writes it."""

from fransys_author.errors import AuthorError

_PREFIX = {
    "device": "-",
    "terminal_strip": "-",
    "cable": "-",
    "harness": "-",
    "add": "-",
    "location": "+",
    "function": "=",
}


def bare(tag: str, call: str) -> str:
    """`tag` unchanged; one that starts with `-`, `+` or `=` raises, naming `call`'s own prefix."""
    if not tag or tag[0] in "-+=":
        msg = f"write {tag[1:] or '<tag>'}; {call}() adds the {_PREFIX[call]}"
        raise AuthorError(msg)
    return tag


def floating_name(tag: str | None, name: str | None, call: str) -> str | None:
    """`name`, after `tag` passes `bare`; a call with neither a tag nor `name=` raises (UT3)."""
    if tag is not None:
        bare(tag, call)
    elif name is None:
        msg = f"give a tag, or name= for a {call.replace('_', ' ')} with no tag"
        raise AuthorError(msg)
    return name
