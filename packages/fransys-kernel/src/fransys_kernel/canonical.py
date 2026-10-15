"""Canonical form: a `Model` as nested data and as byte-stable JSON (design/kernel-model.md 5.6).

A thin front over `encode` (model to data and text) and `decode` (text and data back to a
model). They are separate modules so that `freeze()` can hash a record without importing the
decoder, which itself needs `freeze()`: `encode` -> `hashes` -> `freeze` -> `decode`.
"""

from .decode import from_data
from .encode import to_data, write_json
from .jsonread import read_json
lazy from .model import Model

__all__ = ["dumps", "from_data", "loads", "to_data"]


def dumps(model: Model) -> str:
    """Render `model` as canonical JSON: stable byte-for-byte, for golden files.

    A lone surrogate in a string is written as it is, so a caller that may hold one must
    encode the text with `surrogatepass`; `str.encode("utf-8")` refuses it.
    """
    return write_json(to_data(model))


def loads(text: str) -> Model:
    """Parse `text` as canonical JSON and rebuild the `Model`.

    Raises:
        SchemaError: `text` is not valid canonical JSON, or its envelope is malformed.
        SchemaVersionError: `text` is a schema version this build does not know.
        FreezeError: one or more records could not be built or did not validate.
    """
    return from_data(read_json(text))
