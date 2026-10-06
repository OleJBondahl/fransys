"""Field case: a lowercase second argument of `d.add` is an old key, and raises.

The engineering shape: a cabinet written for 0.5 adds its board as `d.add(board, "io1")`, where
the second argument was a key.

The bug: from UNIT-TAGS on the argument is the printed tag, so `"io1"` would print `-io1` on
every page and in every list, with no sign that the key had become a tag.

The rule (UT5): a `d.add` tag with a lowercase letter raises `AuthorError`, and the message shows
both forms, the uppercase tag and `None` with `name=`. No other tag-form check is added.

The decision that fixes it: author-0019.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys_author import AuthorError


class _Io(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    return _Io(u.device("J1", "DEMO-CONN-2P", interface=True))


@pytest.mark.parametrize("tag", ["io1", "cab", "a2"])
def test_a_tag_with_a_lowercase_letter_raises_and_shows_both_forms(tag: str) -> None:
    d = fr.design("demo_parts", place="C1")
    with pytest.raises(AuthorError) as raised:
        d.add(_board, tag)
    message = str(raised.value)
    assert tag.upper() in message
    assert "None" in message
    assert "name=" in message
