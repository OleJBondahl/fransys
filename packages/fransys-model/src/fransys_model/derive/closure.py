"""Net closure, re-exported from `vocab.closure` (design/connectivity.md, decision 0019).

The union-find lives in `vocab` because `vocab.validators.connectivity` reads it and `vocab`
never imports `derive`; callers keep importing it from here.
"""

from fransys_model.vocab.closure import (
    PhysicalNet,
    net_of,
    physical_nets,
    port_groups,
    port_rails,
    rail_pairs,
)

__all__ = ["PhysicalNet", "net_of", "physical_nets", "port_groups", "port_rails", "rail_pairs"]
