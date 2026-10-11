"""Tests: aliases in `freeze()`, rewritten so a `Model` holds current ids (decision 0014)."""

import pytest
from freeze_probes import (
    draft_of,
    errors_of,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_model.kernel import Origin, RefError, freeze


def test_a_record_that_mentions_no_retired_id_is_kept_as_the_same_object(origin: Origin) -> None:
    """Rewriting rebuilds only what changed."""
    untouched, touched = make_holder("2"), make_holder("3", owner=owner_id("8"))
    draft = draft_of(origin, untouched, touched, make_owner("1"))
    draft.alias(owner_id("8"), owner_id("1"))
    model = freeze(draft)
    assert model.tables["freeze_holder_probe"][untouched.id] is untouched
    assert model.tables["freeze_holder_probe"][touched.id] is not touched


@pytest.mark.parametrize(
    ("aliases", "why"),
    [
        ([("8", "1"), ("1", "8")], "form a cycle"),
        ([("8", "9")], "names no record"),
        ([("2", "1")], "still have a record"),
    ],
    ids=["cycle", "missing-target", "old-still-exists"],
)
def test_an_alias_that_cannot_be_followed_is_a_ref_error_on_the_old_id(
    aliases: list[tuple[str, str]], why: str, origin: Origin
) -> None:
    """Every alias problem is a `RefError` whose holder is the retired id."""
    draft = draft_of(origin, make_owner("1"), make_owner("2"))
    for old, new in aliases:
        draft.alias(owner_id(old), owner_id(new))
    errors = errors_of(draft)
    assert all(isinstance(error, RefError) and error.field == "<alias>" for error in errors)
    assert any(why in str(error) for error in errors)
    assert {error.record_id for error in errors} <= {owner_id(old) for old, _ in aliases}
