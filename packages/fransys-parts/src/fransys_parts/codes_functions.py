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
            "Give one connector function a different `marking` under `[function.connector]`, "
            "or a different `name`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="ENERGY_ON_NON_POWER",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A function whose `kind` is not `supply` or `load` sets `energy`.",
        fix="Remove `energy` from the function, or change its `kind` to `supply` or `load`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="FUNCTION_NAME_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two `[[function]]` entries of one part have the same `name`.",
        fix="Give one of the functions a different `name`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="FUNCTION_WITHOUT_PORTS",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[[function]]` has an empty `ports` list.",
        fix="Add at least one entry to the function's `ports` array, or remove the function.",
        page="findings-parts",
    ),
    CodeInfo(
        code="JOIN_INTO_CONNECTOR",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A header pin's `joins` names a port of a `connector` function.",
        fix="Point `joins` at a port of a non-connector function of the same part.",
        page="findings-parts",
    ),
    CodeInfo(
        code="JOIN_PORT_TWICE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two header pins of one part both `joins` the same function port.",
        fix="Remove the `joins` from one of the two header pins, or point it at a different port.",
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
            "Set `joins` to `<function>.<port>` naming an existing port of another function of "
            "this part."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two `links` entries of one function join the same pair of ports, in either order.",
        fix="Remove the repeated `links` entry.",
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_PORT_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `links` entry's `a` or `b` is not a `name` in the function's `ports`.",
        fix="Set `a` and `b` to names from the function's `ports`, or add the missing port.",
        page="findings-parts",
    ),
    CodeInfo(
        code="LINK_SELF",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `links` entry has the same port as `a` and `b`.",
        fix="Set `b` to a different port from `a`.",
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
        fix="Give one of the channels a different `channel` number, or a different `signal`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="PORT_NAME_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two ports of one function have the same `name`.",
        fix="Rename one of the ports so each port name in the function is unique.",
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
        fix="Rename the port on one of the two functions so the printed designations differ.",
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
            "Keep `power_loss_w` in one place: remove it from `[rating]` or from the "
            "`[function.rating]` it repeats."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_PORT_WITHOUT_SYMBOL",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A port sets `symbol_port`, but its function has no `symbol`.",
        fix="Add a `symbol` to the function, or remove `symbol_port` from the port.",
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_SLUG",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A function's `symbol` is not a lowercase, hyphenated slug.",
        fix=(
            "Rewrite `symbol` in lowercase letters and digits, joined by single hyphens, such "
            "as `change-over-contact`."
        ),
        page="findings-parts",
    ),
)
