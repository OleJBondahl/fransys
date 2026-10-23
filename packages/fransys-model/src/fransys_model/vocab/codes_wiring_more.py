"""More model validator codes about wiring, supplies, PLC and ratings (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="RATING_BREAKING_NO_DATA",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A device states breaking points, but none covers the circuit voltage or time constant."
        ),
        fix=(
            "State a breaking point that covers the circuit voltage and time constant. Write:"
            ' breaking_dc = [{{ voltage_v = "24", current_a = "15000", time_constant_ms = '
            '"10" }}]'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_CURRENT_BELOW_BRANCH",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A function's rated current is below the current its branch can carry.",
        fix=(
            'Use a function rated for the current its branch can carry. Write: current_dc_a = "16"'
        ),
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
        fix=(
            "State the part's voltage rating for the current kind of its rails. Write: "
            'voltage_dc_v = "24"'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="RATING_VOLTAGE_BELOW_CIRCUIT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A function's rated voltage is below the voltage that stands across it.",
        fix=('Use a part rated for the voltage that stands across it. Write: voltage_dc_v = "24"'),
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
        fix=(
            "Declare each supply name once, or twice with identical values. Write: "
            'd.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))'
        ),
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
            "Use an IEC 60757 code: a base code, two combined, a base with a core number, or "
            "SH. Write: d.detail.wire(a, b, wire=(fr.colours.BU, 0.75))"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="WIRE_ON_TWO_HARNESSES",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A wire joins plugs of two harnesses.",
        fix=(
            "Keep each wire within one harness, or join the two harnesses through a cable. "
            "Write: d.pair(a, w1, b)"
        ),
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
            "Give the wire a (colour, size), or a size with a row table; a rail never crosses"
            " a unit boundary. Write: d.detail.wire(a, b, wire=(fr.colours.BU, 0.75))"
        ),
        page="findings-validators",
    ),
)
