"""The tag rules of `d.add` (UT1, UT3, UT5) and the class code of `@unit`."""

import re

from fransys_author.errors import AuthorError

from ._tags import bare

_CLASS_CODE = re.compile(r"[A-Z]{1,3}")


def class_code_of(code: str | None) -> str:
    """`code` for a release's `class_code`, `""` for none; one not 1-3 uppercase letters raises."""
    if not code:
        return ""
    if _CLASS_CODE.fullmatch(code) is None:
        msg = f"class_code {code!r} must be 1 to 3 uppercase letters, as a part file's"
        raise AuthorError(msg)
    return code


def check_add(unit_name: str, class_code: str, tag: str | None, name: str | None) -> str:
    """The key name of an instance; a call that cannot be numbered or keyed raises."""
    if tag is not None:
        bare(tag, "add")
        if tag != tag.upper():
            msg = (
                f"{tag!r} has a lowercase letter, so it is an old key and would print -{tag}; "
                f"write the tag d.add(defn, {tag.upper()!r}), or the floating form "
                f"d.add(defn, None, name={tag!r})"
            )
            raise AuthorError(msg)
        return name or tag
    if name is None:
        msg = "give a tag, or name= for a unit instance with no tag"
        raise AuthorError(msg)
    if not class_code:
        msg = (
            f"unit {unit_name!r} has no class_code, so a floating instance cannot be numbered: "
            "give class_code= on @fr.unit, or write the tag, d.add(defn, 'U1')"
        )
        raise AuthorError(msg)
    return name
