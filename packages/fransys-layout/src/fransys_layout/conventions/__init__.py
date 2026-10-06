"""The conventions layer: tables of choices and orders over named facts, data only.

Imports `geometry` and the model kernel only. Facts register where they are defined; a site
passes its table and the facts to the evaluator (decision layout-0111).
"""

from .evaluate import first_match, holds, keyed, rank_key
from .facts import FACTS, KINDS, SOURCED_KINDS, Fact, fact
from .rows import (
    POLICIES,
    Comb,
    Cond,
    Criterion,
    Order,
    Row,
    Table,
    all_,
    any_,
    not_,
    problems,
    validate,
)

__all__ = (
    "FACTS",
    "KINDS",
    "POLICIES",
    "SOURCED_KINDS",
    "Comb",
    "Cond",
    "Criterion",
    "Fact",
    "Order",
    "Row",
    "Table",
    "all_",
    "any_",
    "fact",
    "first_match",
    "holds",
    "keyed",
    "not_",
    "problems",
    "rank_key",
    "validate",
)
