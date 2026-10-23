"""The old natural order, recorded before the swap to `refdef.natural_key` (LIB-ADOPT R5).

The fixture holds a corpus (goldens' strings and a hand list) sorted by the old kernel key, and the
old `canonical` order of each golden's Id set. Only an entry with a non-ASCII decimal digit may
differ: refdef reads digits as `[0-9]`, the old key read `\\d`. That set is named below.
"""

import json
from pathlib import Path

import pytest
import refdef

from fransys_kernel import Id, canonical

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "natural_orders.json").read_text("utf-8")
)
#: The known difference (ruling LIB-ADOPT N1): the old key read an Arabic-Indic digit as a number.
KNOWN_DIFFERENCE = frozenset({"A٣"})


def _has_non_ascii_decimal(text: str) -> bool:
    return any(c.isdecimal() and not c.isascii() for c in text)


def test_the_known_difference_is_exactly_the_non_ascii_decimal_entries() -> None:
    found = {t for t in _FIXTURE["sorted"] if _has_non_ascii_decimal(t)}
    assert found == KNOWN_DIFFERENCE


def test_the_corpus_sorts_as_it_did_under_the_old_key() -> None:
    old = [t for t in _FIXTURE["sorted"] if t not in KNOWN_DIFFERENCE]
    shuffled = old[::-2] + old[-2::-2]
    assert sorted(shuffled, key=refdef.natural_key) == old
    assert len(old) > 900


@pytest.mark.parametrize("name", sorted(_FIXTURE["canonical_ids"]))
def test_each_golden_id_set_keeps_its_canonical_order(name: str) -> None:
    texts = _FIXTURE["canonical_ids"][name]
    ids = [Id(kind=t.split(":", 1)[0], value=t.split(":", 1)[1]) for t in texts]
    assert [f"{i.kind}:{i.value}" for i in canonical(list(reversed(ids)))] == texts
