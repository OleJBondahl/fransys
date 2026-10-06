"""ITEM-BOX I2b tests: a coil's contact image lists a bare contact, `hide_unused_pins` on or off.

Three changeover poles of one relay: pole 1 is a partner (drawn), pole 2 has no conductor (a
spare), pole 3 has a wire but is not a partner. Only the spare is listed, by its pairs and "N/A".
"""

import pytest
from contact_builders import _port
from test_contact_image_throws import _image

from fransys_model.kernel import Origin, make_id
from fransys_model.layout import Profile
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.enums import ConductorKind, FunctionKind

_POLES = (("11", "12", "14"), ("21", "22", "24"), ("31", "32", "34"))


def _hiding(*, on: bool) -> Profile:
    return Profile(id=make_id(Profile, ("profile",)), key=("profile",), hide_unused_pins=on)


def _wire() -> Conductor:
    """A wire from pole 3's first port to pole 1's: pole 3 is no spare."""
    return Conductor(
        id=make_id(Conductor, ("w",)),
        key=("w",),
        a=_port(3, "31"),
        b=_port(1, "11"),
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def test_a_bare_contact_is_listed_with_its_pairs_and_no_place(origin: Origin) -> None:
    """The bare pole's NO and NC pairs follow the partner's rows, each with "N/A" for a place."""
    # UNDO: derive/drawing_text.py:contact_image, the `spare_entries` call removed
    lines = _image(origin, _POLES, extra=(_hiding(on=True), _wire()), listed=1)
    assert [line.split(" ")[0] for line in lines[1:]] == ["11-14", "21-24"]
    assert lines[2] == "21-24 N/A | 21-22 N/A"
    assert len(lines) == 3


def test_a_contact_with_a_conductor_that_is_not_a_partner_is_not_listed(origin: Origin) -> None:
    """Pole 3 has a wire at 31: it is neither drawn nor bare, so the image skips it."""
    # UNDO: contact_entries.py:_is_bare_contact, `all(` -> `any(`
    lines = _image(origin, _POLES, extra=(_hiding(on=True), _wire()), listed=1)
    assert not any(line.startswith("31-") for line in lines)


@pytest.mark.parametrize("extra", [(), ("off",)])
def test_the_switch_off_or_no_profile_still_lists_a_bare_contact_with_na(
    origin: Origin, extra: tuple[str, ...]
) -> None:
    """The switch no longer gates the spare: off, or with no authored profile, it is listed."""
    # UNDO: derive/drawing_text.py:contact_image, gate the spare block on `hide_unused_pins` again
    records = (_hiding(on=False),) if extra else ()
    lines = _image(origin, _POLES, extra=(*records, _wire()), listed=1)
    assert lines[2] == "21-24 N/A | 21-22 N/A"
    assert len(lines) == 3


def test_a_coil_that_is_the_lone_partner_adds_no_pole_entry(origin: Origin) -> None:
    """A spares-only table's lone partner is its coil: digit-named coil ports give no pole entry."""
    # UNDO: derive/contact_entries.py:contact_entries, remove the `CONTACT_KINDS` early return
    assert _image(origin, (("1", "2", "3"),), kind=FunctionKind.COIL, listed=1) == ["NO | NC"]
