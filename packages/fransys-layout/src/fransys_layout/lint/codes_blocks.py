"""Layout's finding codes of the block and cut stages a consumer acts on."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
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
            "Shorten the stack, move the members to the same end of their columns, or take the "
            "band or mate off one of them ([Drawing well](drawing.md))."
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
            "Split the box into two boxes, or attach fewer columns to it, so every column fits "
            "its card ([Drawing well](drawing.md)). If it still fires, a Fransys defect: send "
            "the smallest model that shows it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="PAGE_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A row of one block is taller than the page, so it stands on a page of its own.",
        fix=(
            "Split the block into smaller groups, or use a larger page "
            "([Drawing well](drawing.md)). If the block is small, a Fransys defect: send the "
            "smallest model that shows it."
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
            "Merge the group with its neighbour or drop its page break, so the page fills "
            "([Drawing well](drawing.md))."
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
            "Reorder the groups so the head and most of its legs share a page "
            "([Drawing well](drawing.md))."
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
            "Attach the symbol to a lane or a box pin, or remove it. If it is wired and still "
            "fires, a Fransys defect: send the smallest model that shows it."
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
            "Wire the box, or remove it. If it is wired and still fires, a Fransys defect: "
            "send the smallest model that shows it."
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
        fix="A Fransys defect: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="CHAIN_NOT_DRAWN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A box that is one hop of a chain of boxes that CHAIN_REFUSED turned away is drawn on "
            "no page; the message names it."
        ),
        fix="Fix the shape CHAIN_REFUSED names, so the chain draws as one column of boxes.",
        page="findings-render",
    ),
    CodeInfo(
        code="CHAIN_REFUSED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "Boxes wired box to box do not make a chain that draws as one column: a ring, a box "
            "joined to three boxes, a box also wired by a trunk, or pins that do not face. The "
            "message names the boxes and the reason."
        ),
        fix=(
            "Wire each box only to the next, with the pins toward the previous box on the north "
            "side and those toward the next on the south side."
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
            "Shorten the row, lower the column count of the block, raise the page width or "
            "set Options.short_height ([Drawing well](drawing.md))."
        ),
        page="findings-render",
    ),
)
