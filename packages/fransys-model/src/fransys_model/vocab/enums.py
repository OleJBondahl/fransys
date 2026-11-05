"""Vocabulary enums: the closed member sets referenced by templates, instances and facets.

Every enum here is registered with `register_enum`, so it is an allowed `Value` leaf, and
holds strings only: enums are written by value (design/kernel-records.md 5.1 and
design/kernel-model.md 5.6). A module that annotates a field with one imports it at runtime, never
under `TYPE_CHECKING`. `kernel.findings.Severity` is the one enum that lives in the kernel instead,
because severity is a kernel concept, not an engineering one.
"""

from enum import Enum

from fransys_model.kernel import register_enum


@register_enum
class PartCategory(Enum):
    """What a `Part` catalog entry is, for numbering and BOM grouping (design/vocabulary.md 6).

    Example: the invented relay example part (design/examples.md 11) is
    `ELECTROMECHANICAL`; a PLC rack module part is `PLC_MODULE`.
    """

    ELECTROMECHANICAL = "electromechanical"
    PROTECTION = "protection"
    TERMINAL = "terminal"
    CABLE = "cable"
    CONNECTOR = "connector"
    PLC_MODULE = "plc_module"
    BOARD = "board"
    GENERIC = "generic"


@register_enum
class FunctionKind(Enum):
    """What kind of `Function` an item exposes.

    Example: the relay `-K1` example has one `COIL` function and `CONTACT_NO`/
    `CONTACT_CO` functions for its contacts.
    """

    COIL = "coil"
    CONTACT_NO = "contact_no"
    CONTACT_NC = "contact_nc"
    CONTACT_CO = "contact_co"
    PROTECTION = "protection"
    SWITCH = "switch"
    TERMINAL = "terminal"
    CONNECTOR = "connector"
    PLC_CHANNEL = "plc_channel"
    SUPPLY = "supply"
    LOAD = "load"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GENERIC = "generic"


@register_enum
class ItemKind(Enum):
    """What an item is, as the overview colours and filters it.

    One value per item. `TERMINAL` is a strip's terminal, `STRIP` the item holding terminals.
    `DEVICE` is everything the other eight do not name.
    """

    TERMINAL = "terminal"
    STRIP = "strip"
    CONNECTOR = "connector"
    PLC_MODULE = "plc_module"
    CABLE = "cable"
    HARNESS = "harness"
    BOARD = "board"
    DEVICE = "device"


@register_enum
class SubjectKind(Enum):
    """What a handle (`Id`) names, for the readers that branch on the kind text of one.

    Example: the id of an item is `ITEM`; the id of a net, mate or any other record is `OTHER`.
    """

    ITEM = "item"
    PORT = "port"
    FUNCTION = "function"
    CONDUCTOR = "conductor"
    UNIT = "unit"
    ASPECT_NODE = "aspect_node"
    OTHER = "other"


@register_enum
class PortBoundary(Enum):
    """Which side of a unit boundary a `Port` is on.

    Example: a terminal's two ports are `INTERNAL` (panel wiring side) and `EXTERNAL`
    (field cable side); which side a wire lands on is this boundary, not a drawing side.
    """

    GENERIC = "generic"
    INTERNAL = "internal"
    EXTERNAL = "external"


@register_enum
class Energy(Enum):
    """Which way energy flows through a `supply` or `load` function's pins (model-0131).

    Example: a redundancy module's two inputs are `supply` functions with `IN`.
    """

    IN = "in"
    OUT = "out"


@register_enum
class ProtectionType(Enum):
    """The device type of a `kind = protection` function, which picks its symbol.

    Example: a `fuse` draws the fuse symbol, an `mcb` the circuit-breaker symbol.
    """

    FUSE = "fuse"
    MCB = "mcb"
    MOTOR_BREAKER = "motor_breaker"
    OVERLOAD = "overload"
    RCD = "rcd"


@register_enum
class NetClass(Enum):
    """What kind of potential or signal a `Net` carries.

    Example: a 24V supply rail is `POWER`; a 4-20mA transmitter loop is `SIGNAL`.
    """

    POWER = "power"
    CONTROL = "control"
    SIGNAL = "signal"
    PE = "pe"
    GENERIC = "generic"


@register_enum
class PowerKind(Enum):
    """What a physical net is on the drawing: a supply, ground, protective earth or none.

    Example: a declared 24 V DC rail is `SUPPLY`, its 0 V rail `GROUND`, a net of class `PE`
    is `PE`, an AC rail or a net in no supply is `NONE`.
    """

    SUPPLY = "supply"
    GROUND = "ground"
    PE = "pe"
    NONE = "none"


@register_enum
class ConductorKind(Enum):
    """What physical realisation a `Conductor` is.

    Example: a panel wire is `WIRE`; one core of the invented cable `W012` example
    is `CORE`; a bridge between two terminals is `JUMPER`.
    `JUMPER`, `MOUNT`, `BUSBAR` and `LEAD` are links: a bridge between terminals,
    plug-on contacts, a rack's power jumper, a device's own lead ending in a pin of a fitted connector.
    A link joins its net and is never a wire: it has no `WireFacet`.
    """

    WIRE = "wire"
    CORE = "core"
    JUMPER = "jumper"
    BUSBAR = "busbar"
    MOUNT = "mount"
    LEAD = "lead"


@register_enum
class Aspect(Enum):
    """One of the three IEC 81346 views of the same objects.

    Example: `-K1` is a `PRODUCT` designation; `+C1` is a `LOCATION` node.
    """

    FUNCTION = "function"
    PRODUCT = "product"
    LOCATION = "location"


@register_enum
class SignalType(Enum):
    """The electrical nature of a PLC channel or field request, read as `fr.SignalType`.

    Example: a 4-20 mA transmitter requests `AI_CURRENT`; a Pt100 requests `RTD`.
    `fr.DI`, `fr.DO`, `fr.AI` and `fr.AO` stay the spelling for `DI`, `DO`, `AI_CURRENT` and
    `AO_CURRENT`; this enum is the home of every other signal, such as `fr.SignalType.RTD`.
    """

    DI = "di"
    DO = "do"
    AI_CURRENT = "ai_current"
    AI_VOLTAGE = "ai_voltage"
    AO_CURRENT = "ao_current"
    AO_VOLTAGE = "ao_voltage"
    RTD = "rtd"
    RELAY = "relay"


@register_enum
class DocumentPreset(Enum):
    """The kind of deliverable a `Document` defines.

    Example: `CABINET_SCHEMATIC` is the document of one cabinet. A preset fixes the default
    page kinds; a new one needs a decision record.
    """

    CABINET_SCHEMATIC = "cabinet_schematic"
    SYSTEM = "system"


@register_enum
class PageKind(Enum):
    """A kind of page in a document, in the one canonical page order.

    Declaration order is the canonical order: a document's pages are its preset's pages plus
    `add`, minus `remove`, in this order, so no project specifies one. The set is closed.
    """

    COVER = "cover"
    NOTES = "notes"
    SHEET_INDEX = "sheet_index"
    CONTENTS = "contents"
    BLOCK_DIAGRAM = "block_diagram"
    SCHEMATIC = "schematic"
    HARNESS_DRAWING = "harness_drawing"
    PLC_LIST = "plc_list"
    TERMINAL_LIST = "terminal_list"
    CONNECTOR_LIST = "connector_list"
    WIRE_LABEL_LIST = "wire_label_list"
    DESIGNATION_LIST = "designation_list"
    CABLE_LIST = "cable_list"
    BOM = "bom"


@register_enum
class ConductorMark(Enum):
    """A conductor designation of IEC 60445; protective earth is a `PinRole`, not one.

    Example: a motor's `U` pin carries `L1`; a PSU's `+` output carries `L+`.
    """

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    N = "N"
    L_PLUS = "L+"
    L_MINUS = "L-"
    M = "M"


@register_enum
class OperatedBy(Enum):
    """What operates a part's contacts, as sold (IEC 60617's "operated by"; parts-0020).

    Example: an e-stop head is `MUSHROOM`; a limit switch is `POSITION`.
    """

    PUSH = "push"
    MUSHROOM = "mushroom"
    TURN = "turn"
    POSITION = "position"
