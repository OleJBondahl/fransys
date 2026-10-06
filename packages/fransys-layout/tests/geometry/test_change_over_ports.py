"""The `change-over-contact` symbol's port names, pinned (CONTACT-STATES Acceptance 6).

Layout may import `electrical_symbols`; the model never does. So the model names a changeover's
throws by role (`PortRole.COMMON`/`BREAK`/`MAKE`), and CS3 binds a changeover's throws to this
symbol's ports by name: common -> `com`, break -> `nc`, make -> `no`. This test fails when the
symbol's port ids change, before that binding silently draws a contact to the wrong pin.
"""

from fransys_layout.geometry import symbol_geometry


def test_the_change_over_contact_has_the_ports_com_nc_and_no() -> None:
    """The ids CS3 binds (common -> com, break -> nc, make -> no), as layout loads the symbol."""
    ports = {port.name for port in symbol_geometry("change-over-contact").ports}
    assert ports == {"com", "nc", "no"}
