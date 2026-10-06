"""The layout engine's house tables key a function kind by its string, which must be a real kind.

`fransys_layout.engines.schematic.defaults` keys `KIND_ROLES` and `SYMBOL_DEFAULTS` (T2)
by the string
value of a `FunctionKind` and imports no `vocab` (layout spec D6, acceptance 6). This test sits
outside the package, where `vocab` may be imported, so a misspelt kind string cannot drift.
"""

from fransys_layout.conventions.symbols import SYMBOL_DEFAULTS
from fransys_layout.engines.schematic.defaults import KIND_ROLES, row_pairs
from fransys_model.vocab.enums import FunctionKind

_KIND_VALUES = {kind.value for kind in FunctionKind}


def test_every_kind_role_key_is_a_function_kind_value() -> None:
    """A misspelt `KIND_ROLES` key would give its kind the plain roles without any error."""
    assert set(KIND_ROLES) <= _KIND_VALUES


def test_every_default_rule_kind_is_a_function_kind_value() -> None:
    """A misspelt `SYMBOL_DEFAULTS` kind would leave its kind with no default symbol."""
    kinds = {row_pairs(row)["function_kind"] for row in SYMBOL_DEFAULTS.rows}
    assert kinds <= _KIND_VALUES


def test_the_kind_roles_table_keys_exactly_the_seven_special_kinds() -> None:
    """A dropped row fails here, since a missing key is no unknown kind string."""
    assert set(KIND_ROLES) == {
        "terminal",
        "connector",
        "plc_channel",
        "coil",
        "contact_no",
        "contact_nc",
        "contact_co",
    }
