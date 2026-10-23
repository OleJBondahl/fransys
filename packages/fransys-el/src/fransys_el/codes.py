"""Finding codes only the placement core emits: its block and cut stages (layout-0358)."""

from fransys_model.kernel import CodeInfo, Severity

from . import codes_netlist

_CORE: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="MARKER_UNPLACED",
        severities=(Severity.WARNING,),
        stage="render",
        who="Fransys",
        cause=(
            "A reference marker has no place inside the page: every level of its stagger leaves "
            "the content box, so layout draws no marker there; the message names its pin and page."
        ),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="OVERLAP",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "Two drawn boxes (symbol bodies, and symbols drawn at a pin end such as a power "
            "symbol), a text and a body, two texts, or a wire and a text meet on one page; the "
            "message names the first of them."
        ),
        fix=(
            "No call clears this: send the smallest model that shows it. The message names the "
            "page and the members."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_OVER_MARKER",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A wire or a junction dot meets the box of a reference marker on one page, or a wire "
            "ends in it; the message names the first of them."
        ),
        fix=(
            "No call clears this: send the smallest model that shows it. The message names the "
            "page and the members."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="OUT_OF_PAGE",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A symbol body or a text lies outside the content box of its page.",
        fix='Split the block that holds it, or use a taller sheet. Write: [paper] default = "A2".',
        page="findings-render",
    ),
    CodeInfo(
        code="ANNEX_UNPLACED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A tag, marking or table beside a symbol found no spot free of every outline, wire "
            "and text; it stands at its first spot, over what blocks it."
        ),
        fix=(
            "No call clears this: shorten the tag of <subject>, or move the symbols around it "
            "to leave a corner free."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ALIGN_DROPPED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "Symbols of a row group or a band rank, mated pins, or the legs of a trunk, "
            "cannot stand level because the stacks in their columns contradict it; "
            "layout dropped the alignment."
        ),
        fix=(
            "Shorten the stack, or move the members to the same end of their columns. Write: "
            "d.layout.chain(a, b) to stand them in one column, source first."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TRUNK_THROUGH_BODY",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A line of a bundle's trunk is drawn through the keep-out of a symbol; the message "
            "names the trunk and the symbol."
        ),
        fix=(
            "No call clears this: send the smallest model that shows it. The trunk is drawn as "
            "placed; stage 5 does not yet stand it clear of bodies."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="CARD_OVERFULL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A box has more attached columns than its card holds; the columns that do not fit "
            "stand free of the card."
        ),
        fix=(
            "No call clears this: wire fewer columns to <subject>, or split the box into two "
            "devices."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="PAGE_OVERFLOW",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause="A row of one block is taller than the page, so it stands on a page of its own.",
        fix=(
            "Split <block> into smaller function blocks, or use a taller sheet. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="FILL_UNDER_MIN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A page is filled less than the minimum because no cut of the blocks fills it more.",
        fix=(
            "Merge the group with its neighbour, or drop its page break, so the page fills. "
            "Write: d.layout.keep_together(a, b) for the neighbouring groups."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="HEAD_OFF_LEGS",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A trunk is cut by a page and its head stands on the page with fewer of its legs.",
        fix=(
            "Reorder the groups so the head and most of its legs share a page. Write: "
            "d.layout.order(a, b) with the head's group first."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="NO_CELL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A symbol is drawn but stands in no cell of any column, or in more cells than it has "
            "elements, so layout places it by no rule; the message names it."
        ),
        fix=(
            "Wire <subject> into a current path, or remove it. Write: d.layout.chain(a, "
            "<subject>) to stand it in a column, source first."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="LANE_WIRE_DROPPED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "Two consecutive cells of a lane have no pin facing each other, or a facing pin on "
            "no net, so no wire is drawn between them; the message names the cells."
        ),
        fix=(
            "Put the facing pins of <subject> and its neighbour on one net. "
            "Write: d.detail.wire(pin_a, pin_b)."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_MEETS_NET",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A fixed wire (a lane wire, join, trunk or drop) meets another net's wire and no "
            "detour exists, so it is drawn as placed; the message names the wire and its ends."
        ),
        fix=(
            "Move a symbol of <subject> or widen the gap beside it so the wire has a free path. "
            "Write: d.layout.chain(a, b) to stand the two symbols in one column."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="NO_BLOCK",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A box is drawn but belongs to no block, or to more than one, so layout places it "
            "by no rule; the message names it."
        ),
        fix=(
            "Wire <subject> to one function block, or remove it. Write: "
            "d.layout.draw_in(<subject>, g) to draw it in a group."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="BLOCK_NOT_PLACED",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "A block stands in no row of any page, or a whole block in more than one, so layout "
            "draws it by no rule; the message names the block and the stage."
        ),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="NOT_SERIES_PARALLEL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="The named symbols are wired as a bridge, which no series or parallel holds.",
        fix="Wire them as series and parallel parts. Write: d.series(a, d.parallel(b, c), d)",
        page="findings-render",
    ),
    CodeInfo(
        code="CHAIN_REFUSED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "Boxes wired box to box do not make a chain that draws as one column: a ring, a box "
            "joined to three boxes, a box also wired by a trunk, or pins that do not face; or a "
            "box in parallel below another box, which has no layout yet. The message names the "
            "boxes and the hop that failed; the boxes are drawn unchained."
        ),
        fix=(
            "Wire each box only to the next, with the pins toward the previous box on the north "
            "side and those toward the next on the south side. Write: d.series(a, b, c). A box in "
            "parallel below another box has no layout yet; it is drawn unchained."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="WIDER_THAN_PAGE",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A row of columns is wider than the page even at its closest spacing.",
        fix=(
            "Shorten the row, lower the column count of the block, or raise the page width. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="PLACEMENT_PROBLEM",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "The placement core cannot take the design, or a set of it; the set draws no page. "
            "The message names the thing and what the core expected."
        ),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="UNKNOWN_SYMBOL_KEY",
        severities=(Severity.ERROR,),
        stage="el",
        who="consumer",
        cause=(
            "A function's chosen symbol key is not in the installed symbol library; it is "
            "drawn as a generic box."
        ),
        fix=(
            "Fix the symbol key of <subject> in its rule, choice or part data, or install a "
            "library version that has it. Write: d.layout.symbol(<target>, <symbol>)"
        ),
        page="findings-render",
    ),
)
FINDING_CODES: tuple[CodeInfo, ...] = (*_CORE, *codes_netlist.FINDING_CODES)
"""The `CodeInfo` rows of the codes only the placement core emits (layout-0358, el-0041).

The mapper `write_findings.kernel_findings` reads them beside `fransys_layout.FINDING_CODES`;
the facade merges them into its registry. A core code the old engines also emit stays in layout.
"""
