"""Tests: record hashes, namespace digests and the model digest.

Each expected hash is `hashlib` over a JSON literal written by hand here, so the code under
test is never checked against itself.
"""

import pytest
from canon_probes import make_owner

from fransys_kernel import Id, SchemaError
from fransys_kernel.hashes import namespace_digests, record_hash

_ONE = "canon_owner_probe:" + "1" * 32
_TWO = "canon_owner_probe:" + "2" * 32


def test_a_lone_surrogate_in_a_record_does_not_break_hashing() -> None:
    """The bytes are encoded with `surrogatepass`, so a stray surrogate hashes, not raises."""
    hashed = record_hash(make_owner("1", ext=frozendict({"x": "\ud800"})))
    assert len(hashed) == 64


def test_a_hash_in_an_unregistered_namespace_is_a_schema_error_not_a_key_error() -> None:
    """`evolve` calls `namespace_digests` with its own map, so the contract is a `ModelError`."""
    with pytest.raises(
        SchemaError, match="namespace 'nowhere', which is not registered"
    ) as excinfo:
        namespace_digests(frozendict({Id(kind="nowhere.x", value="1"): "aa"}), 1)
    assert excinfo.value.kind == "nowhere.x"
