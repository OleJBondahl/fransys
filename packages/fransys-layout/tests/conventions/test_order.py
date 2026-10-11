"""The order tables of `conventions.order`: ids, facts and the load-time checks."""

import fransys_layout.engines.schematic  # noqa: F401 -- importing registers every fact
from fransys_layout.conventions import FACTS, problems
from fransys_layout.conventions.order import BANDS, CHAIN_TIES


def test_the_order_tables_name_registered_facts_only() -> None:
    """Every fact and value in the chain tie order and the band table is registered."""
    assert problems(CHAIN_TIES, FACTS) == []
    assert problems(BANDS, FACTS) == []
