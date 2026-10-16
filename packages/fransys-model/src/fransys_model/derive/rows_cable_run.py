"""The cable blocks of a part run, and the run: the rows the cable drawing pages are cut from."""

from fransys_model.kernel import value


@value
class CableBlockRef:
    """One cable block of a run: its `svgs` key, its run's part number and that run's part line."""

    key: str
    mpn: str
    line: str


@value
class CableRun:
    """One part run: its heading (the part number, or `NO_PART`) and its blocks in their order."""

    heading: str
    blocks: tuple[CableBlockRef, ...]
