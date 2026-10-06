"""The one refusal of a release version or revision below 1 (FD4, decision model-0087)."""

from typing import Any

from fransys_model.kernel import Id, SchemaError

MIN_NUMBER = 1


def refuse_below_one(kind: str, record_id: Id[Any], what: str, field: str, value: int) -> None:
    """Raise `SchemaError` when `value` is an `int` below `MIN_NUMBER`; else do nothing.

    Type-tolerant: a `bool` or any other wrong type passes, because `freeze()` reports the type.
    `what` names the record in the message, `field` the checked field; the error's `kind` is its.
    """
    if type(value) is not int or value >= MIN_NUMBER:
        return
    msg = f"{what} has {field} {value}: a {field} is {MIN_NUMBER} or more"
    holder = record_id if type(record_id) is Id else None
    raise SchemaError(msg, kind=kind, record_id=holder)
