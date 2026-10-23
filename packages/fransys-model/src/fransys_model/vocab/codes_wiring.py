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
            "Use as many cores as the product has colours, each wired or marked spare. Write:"
            " W1.spare()"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONDUCTOR_ON_UNINSTALLED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A conductor lands on an item that is not marked installed.",
        fix=(
            "Mark the item installed, or remove the conductor that lands on it. Write: "
            'd.device("Q9", "DEMO-MCB-3P")'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CORE_ON_PE_NOT_GNYE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A cable core that is not green-yellow (GNYE) lands on a port with role PE; "
            "a screen core (`SH`) is exempt."
        ),
        fix=(
            "The PE core is GNYE (IEC 60204-1): land the GNYE core on the PE port, and another "
            "core elsewhere. Write: W1.core(GNYE, a, b)"
        ),
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
        fix=(
            "Use green-yellow only on the PE net, which `d.earth` declares. Write: d.earth(*pins)"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="LOADS_ABOVE_LIMIT",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="The loads one limit bounds sum above it; none is above it alone.",
        fix=(
            "Lower the loads' summed draw below the limit, or split them across more limits. "
            'Write: nominal_current_a = "0.5"'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="LOAD_ABOVE_LIMIT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A load's stated draw is above the limit that bounds it.",
        fix=(
            "Lower the load's stated draw below its limit, or raise the source's limit. "
            'Write: nominal_current_a = "0.5"'
        ),
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
        fix=(
            "Rewire or separate the nets so no physical net joins two supply potentials. "
            'Write: d.detail.net("name", *pins)'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="NET_ACROSS_UNIT_BOUNDARY",
        severities=(Severity.ERROR, Severity.WARNING),
        stage="validators",
        who="consumer",
        cause=(
            "A declared net joins pins in different units and no wire joins it; a net does not "
            "cross a unit boundary (ERROR when a boundary pin has no other way across)."
        ),
        fix=(
            "Join across the boundary with a wire, and keep nets inside one unit. Write: "
            "d.detail.wire(a, b, wire=...)"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="NET_SHORTED",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="One physical net joins declared nets of different names.",
        fix=(
            "Give one signal one net name, since same-name nets join silently. Write: "
            'd.detail.net("name", *pins)'
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
        fix='Give every port of a bar function the role `pe`. Write: role = "pe"',
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
            "Put every port of the declared net on one board, or wire them into one net. "
            "Write: d.detail.wire(a, b)"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PE_NOT_GNYE",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A single wire on a PE net is not green-yellow (an empty colour is not a finding).",
        fix=(
            "Colour a PE wire green-yellow. Write: d.detail.wire(a, b, wire=(fr.colours.GNYE,"
            " 0.75))"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PE_PORT_OFF_PE",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A port with role PE is on a net that is not PE.",
        fix="Put a port with role PE on the PE net. Write: d.earth(*pins)",
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
        fix=(
            "Bind the request to a channel of the signal type it asked for. Write: "
            'K1.coil.plc(fr.DO, "pump-run")'
        ),
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
        fix=(
            "Wire the request to the channel its binding names, or change the binding. Write:"
            ' K1.coil.plc(fr.DO, "pump-run")'
        ),
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
        fix="Wire both ports of the function. Write: d.detail.wire(a, b)",
        page="findings-validators",
    ),
    CodeInfo(
        code="POTENTIAL_IN_TWO_SUPPLIES",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="One potential name is a rail of two differently named supplies.",
        fix=(
            'Declare each rail name in one supply only. Write: d.dc_supply("24VDC", '
            'd.device("G1", "DEMO-PSU-24"))'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="POTENTIAL_WITHOUT_SUPPLY",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause="A net potential no supply declares: its pins get no rank and no power symbol.",
        fix=(
            'Declare every net potential with a supply. Write: d.dc_supply("24VDC", '
            'd.device("G1", "DEMO-PSU-24"))'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_BREAKING_BELOW_FAULT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A protective device breaks less current than the prospective fault at its position.",
        fix=(
            "Use a protective device that breaks more than the prospective fault current. "
            'Write: breaking_dc = [{{ voltage_v = "24", current_a = "15000" }}]'
        ),
        page="findings-validators",
    ),
)
