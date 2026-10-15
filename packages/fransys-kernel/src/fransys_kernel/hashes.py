"""Hashes: the record hash, the namespace digests and the model digest (design/kernel-model.md 5.6).

All three are SHA-256 over compact canonical JSON, encoded as UTF-8 with `surrogatepass`
so that a stray surrogate in a string hashes instead of raising out of `freeze()`.
Origins are never part of a hash: a moved line is not a change to the plant.
"""

import hashlib
from typing import TYPE_CHECKING, Any

from .encode import _record_data, write_json
from .errors import SchemaError
from .ids import render_id
from .registry import namespace_of, registered_namespaces

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .ids import Id
    from .record import Record
    from .schema import FieldInfo


def record_hash(record: Record) -> str:
    """Return the SHA-256 of `record`'s compact canonical JSON, as hex.

    Resolves `record`'s own class fresh; a caller hashing many records should call `_record_hash`
    with one memo shared across the batch, as nested `@value` types repeat.
    """
    return _record_hash(record, {})


def _record_hash(record: Record, specs: dict[type, FieldInfo]) -> str:
    """`record_hash`, given a `{class: FieldInfo}` memo shared with other records."""
    return _sha256(write_json(_record_data(record, specs), compact=True))


def namespace_digests(hashes: Mapping[Id[Any], str], schema_version: int) -> frozendict[str, str]:
    """Return one digest per registered namespace, empty ones included.

    A digest covers its records' `[id, hash]` pairs in `Id` order, as an array, and the schema.
    An array: a sorted JSON object would put `a.b:` before `a:`, the reverse of `Id` order.
    """
    pairs: dict[str, list[tuple[str, str]]] = {ns: [] for ns in registered_namespaces()}
    for target in sorted(hashes):
        namespace = namespace_of(target.kind)
        if namespace not in pairs:
            msg = f"{render_id(target)} is in namespace {namespace!r}, which is not registered"
            raise SchemaError(msg, kind=target.kind)
        pairs[namespace].append((render_id(target), hashes[target]))
    return frozendict(
        {
            namespace: _sha256(
                write_json(
                    {"records": tuple(records), "schema_version": schema_version}, compact=True
                )
            )
            for namespace, records in pairs.items()
        }
    )


def model_digest(digests: Mapping[str, str]) -> str:
    """Return the SHA-256 over the `[namespace, digest]` pairs, sorted by namespace."""
    return _sha256(write_json(tuple(sorted(digests.items())), compact=True))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()
