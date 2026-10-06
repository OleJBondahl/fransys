"""The engine's `KIND_ROLES` table is what the stages read about function kinds (foundations.md
2.8)."""

from fransys_layout.engines.schematic.defaults import KIND_ROLES, kind_roles
from fransys_layout.stages import KindRoles
from fransys_model.vocab.enums import FunctionKind


def test_links_terminal_kind_is_the_models_terminal_function_kind() -> None:
    """The table names exactly the kinds the stages treat specially, with their roles."""
    assert dict(KIND_ROLES) == {
        FunctionKind.TERMINAL.value: KindRoles(
            terminal=True, narrow=True, boxy=True, sets_group=False
        ),
        FunctionKind.CONNECTOR.value: KindRoles(narrow=True, boxy=True, gendered=True),
        FunctionKind.PLC_CHANNEL.value: KindRoles(boxy=True, sets_group=False, plc_channel=True),
        FunctionKind.COIL.value: KindRoles(coil=True),
        FunctionKind.CONTACT_NO.value: KindRoles(contact=True),
        FunctionKind.CONTACT_NC.value: KindRoles(contact=True, contact_closed=True),
        FunctionKind.CONTACT_CO.value: KindRoles(contact=True, contact_changeover=True),
    }
    assert kind_roles(FunctionKind.LOAD.value) == KindRoles()
