"""The role tables: one row per kind, as data (M2, M3; EL-2a, model-0288).

`FUNCTION_ROLES[kind]` is a plain lookup: no default row and no `.get`. A kind without a row
fails at import (`complete`). Each row's comment names the branch it reproduces.
"""

from .enums import (
    ConductorKind,
    Energy,
    FunctionKind,
    ItemKind,
    LinkKind,
    LinkRest,
    NetClass,
)
from .roles_types import (
    ConductorRole,
    FunctionRole,
    ItemRole,
    LinkRole,
    NetClassRole,
    complete,
)

_F = FunctionKind
_FUNCTION_ROWS: frozendict[FunctionKind, FunctionRole] = frozendict(
    {
        # facts/energy_flow.py:9 takes energy; connectivity.py:148 through; formats.py:112 band
        _F.COIL: FunctionRole(operator=True, through=True, energy=Energy.IN, band="coil"),
        # accessory_blocks.py:18 plain_contact; contacts.py:150 rest; _rest.py:20, _poles.py:15
        _F.CONTACT_NO: FunctionRole(
            contact=True,
            plain_contact=True,
            rest=LinkRest.OPEN,
            through=True,
            band="contact_no",
        ),
        # contacts.py:152 rest "rest" is closed at rest
        _F.CONTACT_NC: FunctionRole(
            contact=True,
            plain_contact=True,
            rest=LinkRest.CLOSED,
            through=True,
            band="contact_nc",
        ),
        # contacts.py:156 a changeover has its rest per throw (by port roles); not in _THROUGH_KINDS
        _F.CONTACT_CO: FunctionRole(
            contact=True, plain_contact=True, changeover=True, band="contact_co"
        ),
        # connectivity.py:148 through; markings.py:90 a protection's conductive link is a pole
        _F.PROTECTION: FunctionRole(protects=True, through=True, band="protection"),
        # _rest.py:20 and _poles.py:15 count SWITCH a contact; accessory_blocks.py:18 does not
        _F.SWITCH: FunctionRole(contact=True, through=True, band="switch"),
        # defaults.py:70 KIND_ROLES terminal, boxy
        _F.TERMINAL: FunctionRole(terminal=True, box=True, band="terminal"),
        # defaults.py:70 KIND_ROLES connector, boxy (a pin group)
        _F.CONNECTOR: FunctionRole(pin_group=True, box=True),
        # defaults.py:70 KIND_ROLES plc_channel, boxy
        _F.PLC_CHANNEL: FunctionRole(channel=True, box=True),
        # derive/facts/energy_flow.py:34 a supply gives energy out
        _F.SUPPLY: FunctionRole(energy=Energy.OUT, band="supply"),
        _F.LOAD: FunctionRole(through=True, energy=Energy.IN, band="load"),
        _F.SENSOR: FunctionRole(band="sensor"),
        _F.ACTUATOR: FunctionRole(through=True, energy=Energy.IN, band="actuator"),
        _F.GENERIC: FunctionRole(),
        # facts/bars.py a bar is a function of its own kind
        _F.BAR: FunctionRole(bar=True),
    }
)
FUNCTION_ROLES = complete(_FUNCTION_ROWS, FunctionKind)

_L = LinkKind
_LINK_ROWS: frozendict[LinkKind, LinkRole] = frozendict(
    {
        # closure.py:26 physical links
        _L.CONDUCTIVE: LinkRole(joins_net=True, passes_rail=True),
        # markings.py:84 pole kinds; contacts.py:61 switched
        _L.SWITCHED: LinkRole(pole=True, switched=True, passes_rail=True),
        # markings.py:84 pole kinds; closure.py:26 a protective link does not join the physical net
        _L.PROTECTIVE: LinkRole(pole=True, protective=True, passes_rail=True),
    }
)
LINK_ROLES = complete(_LINK_ROWS, LinkKind)

_I = ItemKind
_ITEM_ROWS: frozendict[ItemKind, ItemRole] = frozendict(
    {
        # kinds.py terminal_items; marker_targets.py:60 first end, page_nav.py:31 _NO_ENTRY
        _I.TERMINAL: ItemRole(terminal=True),
        # kinds.py:60 strip_set
        _I.STRIP: ItemRole(strip=True),
        # kinds.py:63 an item whose functions are all connectors
        _I.CONNECTOR: ItemRole(connector_housing=True),
        # kinds.py:60 is_plc_module
        _I.PLC_MODULE: ItemRole(plc_module=True),
        # kinds.py:57 is_cable
        _I.CABLE: ItemRole(cable=True),
        # kinds.py:56 is_harness
        _I.HARNESS: ItemRole(harness=True),
        # kinds.py:61 a part with a pcb facet
        _I.BOARD: ItemRole(board=True),
        # kinds.py:62 bar_items
        _I.BAR: ItemRole(bar_holder=True),
        # kinds.py:78 the rest
        _I.DEVICE: ItemRole(),
    }
)
ITEM_ROLES = complete(_ITEM_ROWS, ItemKind)

_C = ConductorKind
_CONDUCTOR_ROWS: frozendict[ConductorKind, ConductorRole] = frozendict(
    {
        # overview_conns.py:25 _PLAIN, contact_lines.py:12 _LANDING; harness_wires.py a single wire
        _C.WIRE: ConductorRole(wire=True, carries=True, lands=True),
        _C.CORE: ConductorRole(carries=True, lands=True),
        # wiring.py:74 and unused.py:65 bridge; power.py:126 rail link; G-POT-20 link, never a wire
        _C.JUMPER: ConductorRole(joins_net=True, bridge=True, rail_link=True),
        _C.BUSBAR: ConductorRole(joins_net=True),
        # enums.py:157 plug-on contacts
        _C.MOUNT: ConductorRole(joins_net=True, mount=True),
        # power.py:126 rail link
        _C.RAIL: ConductorRole(joins_net=True, rail_link=True),
        # leads.py:28 a device's own lead; contact_lines.py:12 _LANDING lands it
        _C.LEAD: ConductorRole(lands=True, joins_net=True, lead=True),
    }
)
CONDUCTOR_ROLES = complete(_CONDUCTOR_ROWS, ConductorKind)

_N = NetClass
_NET_ROWS: frozendict[NetClass, NetClassRole] = frozendict(
    {
        # layout read/roles.py:24 NET_CLASS_TO_ROLE: POWER and PE are the power role
        # (the table now holds PE as earth only, designer 2026-10-16)
        _N.POWER: NetClassRole(power=True),
        # potentials.py:51, potential.py:36, connectivity.py:95 earth is the PE class alone
        _N.PE: NetClassRole(earth=True),
        _N.CONTROL: NetClassRole(control=True),
        # NET_CLASS_TO_ROLE: GENERIC reads as control
        _N.GENERIC: NetClassRole(control=True),
        _N.SIGNAL: NetClassRole(signal=True),
    }
)
NET_CLASS_ROLES = complete(_NET_ROWS, NetClass)
