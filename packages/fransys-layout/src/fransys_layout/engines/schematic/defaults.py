"""House conventions of the schematic engine (foundations.md 2.9, stages.md 6.1, engine.md 7).

Used when a model authors no `layout.symbol_choice`. The symbol table is
`conventions.symbols.SYMBOL_DEFAULTS`; `DEFAULT_RULES` is the stage's view of it. `KIND_ROLES`
keys are the string values of the model enums, and this module imports no `vocab`: a test
outside the package (`tests/test_layout_default_kinds.py`) checks them. The house sheet and
profile, which read the model's layout defaults, are in `read/house.py`.
"""

from fransys_layout.conventions import Comb, Row, Table
from fransys_layout.conventions.symbols import SYMBOL_DEFAULTS, SYMBOL_PORT_MAPS
from fransys_layout.stages import KindRoles, SymbolRule

STAGE_FACTS = frozenset({"function_kind", "part_category", "connector_gender"})

ENGINE_NAME = "schematic"
# The package's `pyproject.toml` version: a test keeps the two equal (decision layout-0029).
ENGINE_VERSION = "0.13.3"

# Whole routing lanes (`WIRING_GRID` each) `place` leaves between the content-box top and
# row 0, so a north-facing port of row 0 routes inside the content box (decision layout-0031).
# Not a profile field: no project tunes it. Three (layout-0048): one lane for the turn, one for
# the wire label that sits flush above the turning segment (layout-0031), and one for the far
# tier of a first-row reference (D4): with `place`'s 24 G lift (one 20 G marker) the first row's
# N port stands 40 G down, and the near tier (C15 push 16 G, box 12 G) plus the far tier (12 G)
# reach 8 + 16 + 12 + 12 = 48 G above it, so one lane (8 G) more.
TOP_HEADROOM_LANES = 3

# Whole routing lanes `place` reserves between the last row and the content-box bottom before
# PAGE_OVERFULL fires, so a south-facing port of a last row left flush against the bottom is
# caught before its route has nowhere to turn (decision layout-0035). Not a profile field, for
# the same reason as the top's. One: the smallest count with which the two-cell south-port
# case (`claude-tools/bottom_symmetry_probe.py`) routes inside the content box.
BOTTOM_HEADROOM_LANES = 1
# Both, as the stages that fit a column to the sheet count them
HEADROOM_LANES = TOP_HEADROOM_LANES + BOTTOM_HEADROOM_LANES


def row_pairs(row: Row) -> dict[str, str]:
    """The `(fact, value)` atoms of a row's condition: a lone pair or an `all_` of pairs."""
    args = row.when.args if isinstance(row.when, Comb) else (row.when,)
    return {a[0]: a[1] for a in args if not isinstance(a, str | Comb)}


def stage_rules(table: Table) -> tuple[SymbolRule, ...]:
    """The `SymbolRule` list `resolve` takes: the rows that read only kind, category, gender."""
    rules = []
    for row in table.rows:
        found = row_pairs(row)
        if found.keys() <= STAGE_FACTS:
            rules.append(
                SymbolRule(
                    kind=found["function_kind"],
                    category=found.get("part_category"),
                    symbol=str(row.then),
                    gender=found.get("connector_gender"),
                    port_map=frozendict(SYMBOL_PORT_MAPS.get(row.id, {})),
                )
            )
    return tuple(rules)


# A rule may carry a `port_map`; only T2.21 does (open-questions.md 7). The model
# cannot tell a fuse from a breaker: a fuse is a `layout.symbol_choice` on its part.
DEFAULT_RULES: tuple[SymbolRule, ...] = stage_rules(SYMBOL_DEFAULTS)

# The kinds the stages treat specially (foundations.md 2.8): stamped into `FunctionSpec.roles` and
# `DrawnFunction.roles`, so a stage reads `roles` and never names a kind. A kind not listed
# has the plain `KindRoles()`.
KIND_ROLES: frozendict[str, KindRoles] = frozendict(
    {
        "terminal": KindRoles(terminal=True, narrow=True, boxy=True, sets_group=False),
        "connector": KindRoles(narrow=True, boxy=True, gendered=True),
        "plc_channel": KindRoles(boxy=True, sets_group=False, plc_channel=True),
        "coil": KindRoles(coil=True, contacts_apart=True),
        "contact_no": KindRoles(contact=True),
        "contact_nc": KindRoles(contact=True, contact_closed=True),
        "contact_co": KindRoles(contact=True, contact_changeover=True),
    }
)


def kind_roles(kind: str) -> KindRoles:
    """The `KindRoles` of function kind value `kind`: its `KIND_ROLES` row, else the plain one."""
    return KIND_ROLES.get(kind, KindRoles())
