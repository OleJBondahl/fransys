"""The model validators' codes about wiring, supplies, PLC and ratings (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CABLE_CORE_COUNT",
        severities=(
            Severity.WARNING,
            Severity.ERROR,
        ),
        stage="validators",
        who="consumer",
        cause=(
            "A cable item's core count differs from its product's core-colour count (WARNING "
            "when fewer, ERROR when more)."
        ),
        fix=(
            "Wire the missing cores, mark a core you leave unused with `w.spare(colour)` (or "
            "`w.spare()` for all the rest), or correct the product's `core_colours` list. A "
            "spare or one-ended screen counts as a core."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONDUCTOR_ON_UNINSTALLED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A conductor lands on an item that is not marked installed.",
        fix="Mark the item installed, or remove the conductor if it is absent.",
        page="findings-validators",
    ),
    CodeInfo(
        code="GNYE_NOT_PE",
        severities=(Severity.ERROR, Severity.WARNING),
        stage="validators",
        who="consumer",
        cause=(
            "A green-yellow conductor is on a net that is not PE: an ERROR on a net a declared "
            "net lists, a WARNING on a net none lists (IEC 60445 keeps green-yellow for PE)."
        ),
        fix="Recolour it, or connect it to the PE net and declare it with `d.earth`.",
        page="findings-validators",
    ),
    CodeInfo(
        code="LOADS_ABOVE_LIMIT",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="The loads one limit bounds sum above it; none is above it alone.",
        fix="If they run together, raise the limit or split the loads.",
        page="findings-validators",
    ),
    CodeInfo(
        code="LOAD_ABOVE_LIMIT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A load's stated draw is above the limit that bounds it.",
        fix="Lower the draw or raise the limit.",
        page="findings-validators",
    ),
    CodeInfo(
        code="NET_POTENTIAL_CONFLICT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "One physical net joins two declared nets that are rails of different supply "
            "potentials."
        ),
        fix="Fix the wiring or net declarations so no net joins two potentials.",
        page="findings-validators",
    ),
    CodeInfo(
        code="NET_SHORTED",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="One physical net joins declared nets of different names.",
        fix=(
            "Fix the wiring, or give the nets one name if they are one signal (same-name nets "
            "join silently)."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="BAR_NOT_PE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A port of a `bar` function has a role other than `pe`. A bar carries protective "
            "earth only, until the copper bar drawing (owner question) is ruled."
        ),
        fix='Set `role = "pe"` on the port in the part file.',
        page="findings-validators",
    ),
    CodeInfo(
        code="NET_UNREALISED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A declared net's ports fall into more than one physical net, and no single board "
            "holds them all. Not for the PE net."
        ),
        fix=(
            "Wire the missing conductors, or remove the ports that should not share the "
            "declared net."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PE_NOT_GNYE",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A single wire on a PE net is not green-yellow (an empty colour is not a finding).",
        fix="Colour the wire GNYE.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PE_PORT_OFF_PE",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A port with role PE is on a net that is not PE.",
        fix="Wire the port to the PE net.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PLC_BINDING_SIGNAL_MISMATCH",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A PLC binding's channel does not have the signal type the request asked for (or "
            "is not a declared channel at all). The message names the asked kind, the channel, "
            "its kind and both fixes."
        ),
        fix="Rewire the request to a channel of the asked kind, or ask for the channel's kind.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PLC_BINDING_WIRING_MISMATCH",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A PLC binding disagrees with the wiring: the request or channel function is wired "
            "to a different channel or request than its binding."
        ),
        fix="Rebind the request/channel to match the wiring, or rewire it to match the binding.",
        page="findings-validators",
    ),
    CodeInfo(
        code="FUNCTION_HALF_CONNECTED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A two-port coil, load, contact, switch, protection or actuator is connected "
            "at one port and open at the other."
        ),
        fix="Wire the open port, or remove the half-wired function.",
        page="findings-validators",
    ),
    CodeInfo(
        code="POTENTIAL_IN_TWO_SUPPLIES",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="One potential name is a rail of two differently named supplies.",
        fix=(
            "Rename one of the potentials, or merge the two supply declarations if they are "
            "the same supply."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="POTENTIAL_WITHOUT_SUPPLY",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A net potential no supply declares: its pins get no rank and no power symbol.",
        fix="Declare the supply with that rail.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_BREAKING_BELOW_FAULT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A protective device breaks less current than the prospective fault at its position.",
        fix="Fit a higher-breaking device.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_BREAKING_NO_DATA",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A device states breaking points, but none covers the circuit voltage or time constant."
        ),
        fix="Add a point for that voltage or time constant.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_CURRENT_BELOW_BRANCH",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A function's rated current is below the current its branch can carry.",
        fix="Fit a part rated for the branch's current, or reduce the limit that sets the bound.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_CURRENT_KIND_UNSTATED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A function's part states a voltage rating for AC or for DC only, and the function "
            "stands on rails of the other current kind."
        ),
        fix="State the missing voltage rating in the part, or use a part rated for that kind.",
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_VOLTAGE_BELOW_CIRCUIT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A function's rated voltage is below the voltage that stands across it.",
        fix=(
            "Fit a part rated for the circuit's voltage, or change the supply or wiring to "
            "lower it."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="SUPPLY_DIFFERS",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "Two declarations of one supply name disagree in current, earthing or rails, or "
            "two source declarations in fault current or time constant."
        ),
        fix="Make them agree, or give the differing declarations distinct names.",
        page="findings-validators",
    ),
    CodeInfo(
        code="WIRE_COLOUR_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A wire or cable-product core colour is not a recognized IEC 60757 colour code (or "
            "combination)."
        ),
        fix=(
            "Use a base code, a combination of two, a base code with a core number, or shield "
            "code `SH`."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="WIRE_ON_TWO_HARNESSES",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A wire joins plugs of two harnesses.",
        fix="Wire to a plug of one harness, or use a cable.",
        page="findings-validators",
    ),
    CodeInfo(
        code="WIRE_ROW_UNRESOLVED",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "A series or detail wire was written without a row, and at build end its net carries "
            "no rail of its unit, states no `source_row` and holds no PLC channel signal, or "
            "carries rails of two rows. The message names the net and the wire's two pins."
        ),
        fix=(
            "Give `wire=` on that series: a `(colour, size)`, or a size with a row table. A rail "
            "never reaches a wire across a unit boundary from its container."
        ),
        page="findings-validators",
    ),
)
