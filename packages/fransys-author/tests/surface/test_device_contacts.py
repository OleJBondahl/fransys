"""HA8: `d.device(..., contacts=)` writes one `ContactsFacet`; a refused call writes nothing."""

from typing import ClassVar

import pytest
from fransys_author import AuthorError
from fransys_author.surface import TypedDevice, design

from fransys_model.vocab import ContactFit, ContactsFacet, Part
lazy from fransys_model.kernel import Draft


class Housing(TypedDevice):
    mpn: ClassVar[str] = "TEST-CONN-2P"


def _facets(d) -> list[ContactsFacet]:
    return [r for r in d.draft().records() if isinstance(r, ContactsFacet)]


def _part_id(parts: Draft, mpn: str):
    (part,) = (r for r in parts.records() if isinstance(r, Part) and r.mpn == mpn)
    return part.id


def test_one_mpn_fits_every_used_pin(parts: Draft) -> None:
    d = design(parts, place="C1")
    p1 = d.device("P1", "TEST-CONN-2P", contacts="TEST-CRIMP")
    (facet,) = _facets(d)
    assert facet.subject == p1.id
    assert facet.fits == (ContactFit(pin=None, part=_part_id(parts, "TEST-CRIMP")),)


def test_a_mapping_fits_by_pin_sorted(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.device("P1", "TEST-CONN-2P", contacts={"2": "TEST-CRIMP", "1": "TEST-CRIMP"})
    (facet,) = _facets(d)
    crimp = _part_id(parts, "TEST-CRIMP")
    assert facet.fits == (ContactFit(pin="1", part=crimp), ContactFit(pin="2", part=crimp))


def test_a_part_class_takes_contacts(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.device("P1", Housing, contacts="TEST-CRIMP")
    assert len(_facets(d)) == 1


def test_no_contacts_writes_no_facet(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.device("P1", "TEST-CONN-2P")
    assert _facets(d) == []


@pytest.mark.parametrize(
    ("mpn", "contacts", "text"),
    [
        ("TEST-CONN-2P", {"9": "TEST-CRIMP"}, "pin '9'"),
        ("TEST-CONN-2P", {}, "empty mapping"),
        ("TEST-CONN-2P", "NO-SUCH-CONTACT", "NO-SUCH-CONTACT"),
        ("TEST-CONN-2P", {"1": "NO-SUCH-CONTACT"}, "NO-SUCH-CONTACT"),
        ("TEST-RLY-2CO", "TEST-CRIMP", "needs a connector part"),
    ],
)
def test_a_refused_call_writes_nothing(parts: Draft, mpn: str, contacts, text: str) -> None:
    d = design(parts, place="C1")
    before = len(d.draft().records())
    with pytest.raises(AuthorError, match=text):
        d.device("P1", mpn, contacts=contacts)
    assert len(d.draft().records()) == before
