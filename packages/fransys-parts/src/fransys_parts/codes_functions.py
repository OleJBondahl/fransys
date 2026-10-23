"""Part-file finding codes about functions, ports, links and joins (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CONNECTOR_MARKING_REUSED",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "Two connector functions of one part print the same label, their `marking` or else "
            "their `name`."
        ),
        fix=(
            "Each connector prints its own label, its `marking` or else its `name`. "
            'Write: marking = "X2"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="ENERGY_ON_NON_POWER",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A function whose `kind` is not `supply` or `load` sets `energy`.",
        fix='Only a `supply` or `load` function takes `energy`. Write: kind = "load"',
        page="findings-parts",
    ),
    CodeInfo(
        code="FUNCTION_NAME_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two `[[function]]` entries of one part have the same `name`.",
        fix='Each `[[function]]` has its own `name`. Write: name = "co_3"',
        page="findings-parts",
    ),
    CodeInfo(
        code="BAR_SYMBOL",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `bar` function names a `symbol`; a bar is never drawn.",
        fix=('A `bar` function takes no `symbol`, since a bar is never drawn. Write: kind = "bar"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="FUNCTION_WITHOUT_PORTS",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[[function]]` other than a `bar` has an empty `ports` list.",
        fix=(
            "A `[[function]]` other than a `bar` lists at least one port in `ports`. "
            'Write: ports = [{{ name = "1", role = "generic" }}]'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="JOIN_INTO_CONNECTOR",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A header pin's `joins` names a port of a `connector` function.",
        fix=(
            "A header pin `joins` a port of a non-connector function of the same part. "
            'Write: joins = "k1.A1"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="JOIN_PORT_TWICE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two header pins of one part both `joins` the same function port.",
        fix=('Each function port is joined by at most one header pin. Write: joins = "k1.A2"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="JOIN_PORT_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A header pin's `joins` value does not name a port of a function in this part, or "
            "is not `<function>.<port>`."
        ),
        fix=(
            "`joins` is `<function>.<port>`, naming a port of another function of this part. "
            'Write: joins = "k1.A1"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two `links` entries of one function join the same pair of ports, in either order.",
        fix=(
            "Each pair of ports is linked once in a function, in either order. "
            'Write: links = [{{ a = "11", b = "12", kind = "switched" }}]'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_PORT_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `links` entry's `a` or `b` is not a `name` in the function's `ports`.",
        fix='Each `a` and `b` names a port listed in `ports`. Write: a = "11"',
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_SELF",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `links` entry has the same port as `a` and `b`.",
        fix='`a` and `b` name two different ports. Write: b = "12"',
        page="findings-parts",
    ),
    CodeInfo(
        code="PLC_CHANNEL_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "Two `[function.plc_channel]` tables of one part have the same `channel` and `signal`."
        ),
        fix="Each `[function.plc_channel]` has its own `channel` and `signal`. Write: channel = 4",
        page="findings-parts",
    ),
    CodeInfo(
        code="PORT_NAME_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two ports of one function have the same `name`.",
        fix='Each port of one function has its own `name`. Write: name = "A2"',
        page="findings-parts",
    ),
    CodeInfo(
        code="PORT_NAME_SHARED",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "Two functions of one part give a port the same name, and their printed "
            "designations would be the same."
        ),
        fix=(
            "Each port name is unique across the part, so the printed designations differ. "
            'Write: name = "A3"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="POWER_LOSS_TWICE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "`power_loss_w` is set both in the part's `[rating]` and in a function's "
            "`[function.rating]`."
        ),
        fix=(
            "`power_loss_w` is stated once, in `[rating]` or in one `[function.rating]`. "
            'Write: power_loss_w = "2.5"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_PORT_WITHOUT_SYMBOL",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A port sets `symbol_port`, but its function has no `symbol`.",
        fix=(
            "A port with `symbol_port` needs its function to have a `symbol`. "
            'Write: symbol = "operating-device"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_SLUG",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A function's `symbol` is not a lowercase, hyphenated slug.",
        fix=(
            "`symbol` is lowercase letters and digits joined by single hyphens, such as "
            '`change-over-contact`. Write: symbol = "change-over-contact"'
        ),
        page="findings-parts",
    ),
)
