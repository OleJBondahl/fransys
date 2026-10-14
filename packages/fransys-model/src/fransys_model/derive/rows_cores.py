"""The row shape of an open core: a spare, or a screen earthed at one end (CC7, model-0204)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Item, Port


@value
class OpenCoreRow:
    """One open core of one cable: the facts of a `CableRow`, with at most one end.

    `at` is the port the one end lands on, `None` when it lands nowhere; `at_designation` is its
    printed designation, `""` for none. `spare` is false for a screen (an `SH` core), true for
    any other open core.
    """

    cable: Id[Item]
    cable_designation: str
    index: int
    colour: str
    at: Id[Port] | None
    at_designation: str
    spare: bool


@value
class CoreListRow:
    """One line of the core list: a core with its ends, its pair word and its spare mark.

    Every text is a field of a `CableRow` or an `OpenCoreRow` or `core_pair_word`; `""` is none.
    """

    cable: str
    core: int
    colour: str
    pair: str
    end_a: str
    end_b: str
    note: str
