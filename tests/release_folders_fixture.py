"""One small board unit and its releases, from demo parts only (WORKFLOW-BLOCKS tests)."""

import fransys as fr
import fransys_author


def build_board(*, version=1, revision=1, history=None, colour="BU"):
    """`(result, scope)` of one board unit; `history` is `(version, revision, date)` triples."""
    entries = history if history is not None else [(version, revision, "2026-09-26")]
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    s = design.scope("wb")
    u = s.unit("wb-board", version=version, revision=revision, interface="1")
    for entry_version, entry_revision, date in entries:
        u.revision(
            entry_revision,
            version=entry_version,
            date=date,
            text=f"Revision {entry_version}.{entry_revision}",
            created="OJB",
        )
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour=colour, gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1)
    return fr.build(parts, design.draft()), u


def release_board(into, **kwargs):
    """Release one board unit into `into` and return the folder."""
    result, scope = build_board(**kwargs)
    return fr.release(result, into, unit=scope)


def build_system(*, revision=1, history):
    """The system build: one project at version 1, `history` as `(version, revision, date)`."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    design.project(
        title="WB system", number="P-WB", customer="Demo", revision=revision, author="OJB"
    )
    for version, entry_revision, date in history:
        design.revision(
            entry_revision,
            version=version,
            date=date,
            text=f"Revision {entry_revision}",
            created="OJB",
        )
    return fr.build(parts, design.draft())


def build_cabinet(*, board_revision=1, extra_wire=False, with_board=True):
    """`(result, cabinet scope)`: a cabinet unit nesting the board of `board_revision` once.

    `extra_wire` adds a cabinet-side wire (a conductor and a net); `with_board=False` leaves the
    board out.
    """
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    u = design.scope("cab").unit("wb-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-09-26", text="First release", created="OJB")
    place = u.location("C1", "Cabinet")
    grp = u.group("FLD", "Field wiring")
    p1 = u.item("DEMO-CONN-2P", tag="P1", at=place, group=grp)
    if extra_wire:
        p2 = u.item("DEMO-CONN-2P", tag="P2", at=place, group=grp)
        u.wiring(colour="BU", gauge="0.5")(p1["1"], p2["1"])
    if with_board:
        board = _board(u.scope("brd", at=place), board_revision)
        u.mate(p1, board)
    return fr.build(parts, design.draft()), u


def _board(scope, revision):
    u = scope.unit("wb-board", version=1, revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    u.boundary(x1)
    return x1
