"""WP6 tests: record hashes, namespace digests and the model digest (design/kernel-model.md 5.6).

Each expected hash is `hashlib` over a JSON literal written by hand here, so the code under
test is never checked against itself.
"""

import hashlib
from decimal import Decimal
from typing import Any

import pytest
from canon_probes import CanonDetail, Shade, make_item, make_owner, owner_id

from fransys_model.kernel import Id, SchemaError, register_namespaces
from fransys_model.kernel.hashes import model_digest, namespace_digests, record_hash
from fransys_model.kernel.ids import render_id

_ONE = "canon_owner_probe:" + "1" * 32
_TWO = "canon_owner_probe:" + "2" * 32


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_a_record_hash_is_sha256_of_its_compact_canonical_json() -> None:
    """Keys sorted, no spaces, every field present."""
    expected = '{"ext":{},"id":"' + _ONE + '","key":["1"]}'
    assert record_hash(make_owner("1")) == _sha(expected)


def test_a_record_hash_reads_ext_and_key_too() -> None:
    """Nothing about a record is left out of its hash."""
    changed_key = make_owner("1")
    object.__setattr__(changed_key, "key", ("other",))
    assert record_hash(changed_key) != record_hash(make_owner("1"))
    assert record_hash(make_owner("1", ext=frozendict({"x": 1}))) != record_hash(make_owner("1"))


def test_a_record_hash_reads_a_nested_value_and_its_reference_too() -> None:
    """model-0102 (PERF-FREEZE, B8): a class's fields are resolved through a shared memo now,
    keyed by class, not by kind -- so a nested `@value`'s hash must still be byte-identical.
    """
    detail = CanonDetail(amount=Decimal("2.50"), owner=owner_id("1"), shade=Shade.BLUE)
    item = make_item("2", details=(detail,))
    expected = (
        '{"amount":"1.5","count":3,"details":[{"amount":"2.5",'
        '"owner":"' + _ONE + '","shade":"blue"}],"ext":{},"flag":true,'
        '"id":"canon_item_probe:' + "2" * 32 + '","key":["2"],"level":2,"maybe":null,'
        '"name":"pump","note":null,"owner":"' + _ONE + '","scores":{"x":1},'
        '"shade":"red","tags":["a","b"]}'
    )
    assert record_hash(item) == _sha(expected)


def test_a_lone_surrogate_in_a_record_does_not_break_hashing() -> None:
    """The bytes are encoded with `surrogatepass`, so a stray surrogate hashes, not raises."""
    hashed = record_hash(make_owner("1", ext=frozendict({"x": "\ud800"})))
    assert len(hashed) == 64


def test_a_namespace_digest_hashes_the_id_ordered_pairs_and_the_schema_version() -> None:
    """Records as an array of `[id, hash]` in `Id` order, beside `schema_version`."""
    hashes: Any = frozendict({owner_id("2"): "bb", owner_id("1"): "aa"})
    expected = '{"records":[["' + _ONE + '","aa"],["' + _TWO + '","bb"]],"schema_version":1}'
    assert namespace_digests(hashes, 1)["core"] == _sha(expected)


def test_the_schema_version_is_part_of_every_digest() -> None:
    """The same records under another version give another digest."""
    hashes: Any = frozendict({owner_id("1"): "aa"})
    assert namespace_digests(hashes, 1)["core"] != namespace_digests(hashes, 2)["core"]


def test_there_is_a_digest_for_every_registered_namespace_even_an_empty_one() -> None:
    """`digests` follows the namespaces registered in the process; empty ones hash to no records."""
    register_namespaces("facet", "layout")
    digests = namespace_digests(frozendict(), 1)
    assert set(digests) == {"core", "facet", "layout"}
    assert digests["facet"] == _sha('{"records":[],"schema_version":1}')


def test_a_record_only_moves_its_own_namespaces_digest() -> None:
    """Changing a `core` record changes the `core` digest and leaves `facet` and `layout` alone."""
    register_namespaces("facet", "layout")
    before = namespace_digests(frozendict({owner_id("1"): "aa"}), 1)
    after = namespace_digests(frozendict({owner_id("1"): "zz"}), 1)
    assert before["core"] != after["core"]
    assert before["facet"] == after["facet"]
    assert before["layout"] == after["layout"]


def test_records_are_ordered_by_id_not_by_their_rendered_text() -> None:
    """`Id` order puts `facet.a` before `facet.a2`, but the text `facet.a2:1` sorts first.

    Only sorting by `Id` gives `p` first, so this fails if the pairs are ordered as strings.
    """
    register_namespaces("facet", "layout")
    prefix = Id(kind="facet.a", value="1")
    longer = Id(kind="facet.a2", value="1")
    assert render_id(longer) < render_id(prefix)
    assert prefix < longer
    hashes: Any = frozendict({longer: "d", prefix: "p"})
    expected = '{"records":[["facet.a:1","p"],["facet.a2:1","d"]],"schema_version":1}'
    assert namespace_digests(hashes, 1)["facet"] == _sha(expected)


def test_the_model_digest_hashes_the_sorted_namespace_digest_pairs() -> None:
    """An array of `[namespace, digest]`, sorted by namespace."""
    digests: Any = frozendict({"facet": "f", "core": "c"})
    assert model_digest(digests) == _sha('[["core","c"],["facet","f"]]')


def test_a_hash_in_an_unregistered_namespace_is_a_schema_error_not_a_key_error() -> None:
    """`evolve` calls `namespace_digests` with its own map, so the contract is a `ModelError`."""
    with pytest.raises(
        SchemaError, match="namespace 'nowhere', which is not registered"
    ) as excinfo:
        namespace_digests(frozendict({Id(kind="nowhere.x", value="1"): "aa"}), 1)
    assert excinfo.value.kind == "nowhere.x"
