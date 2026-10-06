"""The order tables of `conventions.order`: ids, facts and the load-time checks."""

import fransys_layout.engines.schematic  # noqa: F401 -- importing registers every fact
from fransys_layout.conventions import FACTS, problems
from fransys_layout.conventions.order import BANDS, CHAIN_TIES


def test_the_order_tables_name_registered_facts_only() -> None:
    """Every fact and value in the chain tie order and the band table is registered."""
    assert problems(CHAIN_TIES, FACTS) == []
    assert problems(BANDS, FACTS) == []


def test_the_chain_tie_criteria_keep_the_designation_last() -> None:
    """A6 is a proxy for the concept the model lacks, so it is the last rule tried."""
    assert [c.id for c in CHAIN_TIES.criteria] == ["D1vote", "C20", "A6"]
