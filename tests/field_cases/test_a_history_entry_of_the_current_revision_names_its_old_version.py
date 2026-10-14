"""Field case: a history entry with no `version` that repeats the unit's current revision.

The engineering shape: a unit at version 2, revision 2, whose `history=` lists revision 1 and
revision 2 of the old release and names no `version`. An entry with no `version` takes the
unit's current version, so the history's revision 2 meets the release's own revision 2 record.

The bug (0.18.6): the build raised a bare `MergeConflict` from the draft, naming neither the entry
nor a fix. The rule: `d.add` raises `AuthorError` naming the entry (version.revision and text)
and "give the entry its old `version=`" (author-0048).
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest


class _Io(NamedTuple):
    X1: Any


def _entry(revision: int, text: str) -> dict[str, str | int]:
    return {"revision": revision, "date": "2026-01-01", "text": text, "created": "AB"}


@fr.unit(
    "history-board",
    revision=2,
    interface_version=1,
    version=2,
    date="2026-02-02",
    text="second revision of version 2",
    by="AB",
    history=[_entry(1, "first release"), _entry(2, "old second release")],
)
def _board(d: Any) -> _Io:
    return _Io(X1=d.device("X1", "DEMO-CONN-2P", interface=True))


def test_a_history_entry_without_version_that_meets_the_current_revision_is_an_author_error() -> (
    None
):
    """The error names `2.2`, the entry text and the fix."""
    d = fr.design("demo_parts")
    with pytest.raises(fr.AuthorError) as caught:
        d.add(_board, "U1")
    message = str(caught.value)
    assert "2.2" in message
    assert "old second release" in message
    assert "give the entry its old `version=`" in message


def test_the_same_history_with_the_old_version_named_builds() -> None:
    """Naming `version=1` on both old entries removes the collision."""
    old = [{**_entry(1, "first release"), "version": 1}, {**_entry(2, "old second"), "version": 1}]
    board = fr.unit(
        "history-board",
        revision=2,
        interface_version=1,
        version=2,
        date="2026-02-02",
        text="second revision of version 2",
        by="AB",
        history=old,
    )(_board.build)
    fr.design("demo_parts").add(board, "U1")
