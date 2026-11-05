"""The tag rules of `d.add`."""

from fransys_author.errors import AuthorError

from ._tags import bare


def check_add(tag: str, name: str | None) -> str:
    """The key name of an instance: `name=` if given, else its tag; a tag that cannot be keyed raises."""
    bare(tag, "add")
    if tag != tag.upper():
        msg = f"{tag!r} has a lowercase letter, so it is an old key and would print -{tag}; write the tag d.add(defn, {tag.upper()!r})"
        raise AuthorError(msg)
    return name or tag
