"""Field case: two members of a net, one under an attached terminal, lose their join silently.

The engineering shape: the top pins of two indicator lamps, each on the top row of neighbouring
columns and wired together. A feed-through terminal wired to the second lamp's pin attaches above
that lamp, so its pin stands a row lower than the first lamp's. The wire turns back past the
first lamp and is no join. (The members were PLC card pins until V1 gave a module one
box with its channels as pins; the shape needs only column ends.)

The bug: the two members lost their join with no wire reference and no finding, because no run
had joined either end (V6 only named a turned wire with an end a run joined).
The rule (decision layout-0099): a pin with an attached part above it
either aligns with its run or gives `JOIN_UNALIGNED`, an INFO (layout-0252).
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU


def _build(*, attached: bool) -> fr.BuildResult:
    """The shape above, one cabinet document."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        first = d.device("P1", "DEMO-LAMP-24")
        second = d.device("P2", "DEMO-LAMP-24")
        d.detail.wire(first.lamp["1"], second.lamp["1"], wire=(BU, 0.5))
        if attached:
            terminal = d.device("X1", "DEMO-TB-2.5")
            d.detail.wire(terminal.terminal["external"], second.lamp["1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _unaligned(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == "JOIN_UNALIGNED"]


def test_the_unshifted_pair_gives_no_finding() -> None:
    """The control: no attached terminal, no finding."""
    assert _unaligned(_build(attached=False)) == []


def test_a_member_under_an_attached_terminal_gives_join_unaligned() -> None:
    """The shifted pair is an INFO naming the two ports, never silence."""
    found = _unaligned(_build(attached=True))
    assert len(found) == 1
    assert found[0].severity is fr.Severity.INFO
    assert "-P1:1" in found[0].message
    assert "-P2:1" in found[0].message
