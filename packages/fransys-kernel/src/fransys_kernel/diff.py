"""`diff()`: compare two models by record hash (design/kernel-model.md 5.7)."""

from typing import Any

from .errors import SchemaError
from .ids import Id
from .model import Model
from .record import value


@value
class ModelDiff:
    """Ids added, removed, or changed between two models, by record hash.

    Drives golden tests and incremental re-rendering. Each tuple is in `Id` order.
    """

    added: tuple[Id[Any], ...]
    removed: tuple[Id[Any], ...]
    changed: tuple[Id[Any], ...]


def diff(a: Model, b: Model) -> ModelDiff:
    """List exactly the ids whose record hash differs between `a` and `b`.

    `added` is in `b` only, `removed` in `a` only, `changed` in both with different content.
    Origins are not compared (a moved line is not a change), and neither are aliases: they
    are not records.

    Raises:
        SchemaError: `a` or `b` is not a `Model`.
    """
    for side in (a, b):
        if not isinstance(side, Model):
            msg = f"diff compares two Models, not a {type(side).__name__}"
            raise SchemaError(msg, kind="diff")
    before, after = a.hashes, b.hashes
    return ModelDiff(
        added=tuple(sorted(after.keys() - before.keys())),
        removed=tuple(sorted(before.keys() - after.keys())),
        changed=tuple(
            sorted(
                target for target in before.keys() & after.keys() if before[target] != after[target]
            )
        ),
    )
