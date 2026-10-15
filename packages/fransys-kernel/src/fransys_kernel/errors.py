"""Kernel errors.

Structural problems, raised at the boundary and never silenced (design/kernel-model.md 5.8, decision
0006). Engineering problems are not here: a domain validator returns a `Finding`
(`kernel.findings`) instead of raising.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ids import Id
    from .origin import Origin


class ModelError(Exception):
    """Base of every structural error.

    Schema, value type, reference, merge and version problems all raise; none of them
    is a `Finding`.
    """


class SchemaError(ModelError):
    """A record fails its own schema.

    A required field is missing, or `kind` is already registered to a different class.
    `kind` holds the class name when the class has no kind at all.
    """

    def __init__(self, message: str, *, kind: str, record_id: Id[Any] | None = None) -> None:
        """Record which `kind` the violation was found on, and the record that has it.

        `record_id` is `None` when the problem is a class's, not a record's: its
        annotations, a kind registered twice.
        """
        super().__init__(message)
        self.kind = kind
        self.record_id = record_id


class ValueTypeError(ModelError):
    """A value, or something nested in it, is outside the closed set in kernel-records.md 5.1."""

    def __init__(
        self, message: str, *, path: tuple[str, ...], record_id: Id[Any] | None = None
    ) -> None:
        """Record `path` to the offending value, and the record that holds it if known.

        `check_value` does not know the record, so `freeze()` adds it.
        """
        super().__init__(message)
        self.path = path
        self.record_id = record_id


class RefError(ModelError):
    """An `Id[K]` reference field names an id that does not exist.

    Or that exists under the wrong kind.
    """

    def __init__(self, message: str, *, record_id: Id[Any], field: str, target: Id[Any]) -> None:
        """Record the `record_id` that holds the bad reference, its `field`, and its `target`.

        `field` is a dotted path inside a nested `@value` (`"profile.owner"`).
        A dangling `target` has no origin, so the holder's origin is what `describe` shows.
        """
        super().__init__(message)
        self.record_id = record_id
        self.field = field
        self.target = target


class MergeConflict(ModelError):  # noqa: N818 -- design/kernel-model.md 5.8, GLOSSARY.md name it
    """Two drafts or models declare the same id with different content.

    Nothing wins silently: both origins are named.
    """

    def __init__(
        self, message: str, *, record_id: Id[Any], origin_a: Origin, origin_b: Origin
    ) -> None:
        """Record the conflicting `record_id` and both authoring origins.

        `record_id` is the id both sides declared with different content; `origin_a` is where
        the first declaration was authored and `origin_b` the second.
        """
        super().__init__(message)
        self.record_id = record_id
        self.origin_a = origin_a
        self.origin_b = origin_b


class SchemaVersionError(ModelError):
    """`from_data` was given a `schema_version` this build does not know.

    There is no migration framework.
    """

    def __init__(self, message: str, *, expected: int, actual: int) -> None:
        """Record the `expected` and `actual` schema versions."""
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class FreezeError(ModelError):
    """Aggregates every error `freeze()` found.

    So an author fixes a batch, not one error per run.
    """

    def __init__(self, errors: tuple[ModelError, ...]) -> None:
        """Store every collected `errors` entry, in the order given.

        `freeze()` sorts them, so the list never depends on the order records were added.
        """
        super().__init__(f"{len(errors)} error(s) during freeze")
        self.errors = errors
