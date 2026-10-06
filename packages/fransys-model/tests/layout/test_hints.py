"""WP18 tests: authored layout kinds (ROADMAP WP18, design/layout-namespace.md)."""

import pytest
from layout_examples import function_id, template_id

from fransys_model.kernel import Id, SchemaError
from fransys_model.layout import Chain, ChainEntry, OrderHint, SymbolChoice
from fransys_model.vocab.enums import FunctionKind


def _chain(*entries: ChainEntry) -> Chain:
    return Chain(
        id=Id(kind="layout.chain", value="1" * 32),
        key=("examples", "layout", "pump1", "power"),
        entries=entries,
    )


def _choice(*, function: bool, kind: bool, template: bool = False) -> SymbolChoice:
    return SymbolChoice(
        id=Id(kind="layout.symbol_choice", value="2" * 32),
        key=("examples", "layout", "choice"),
        function=function_id("a") if function else None,
        template=template_id("t") if template else None,
        part=None,
        kind=FunctionKind.CONTACT_NO if kind else None,
        symbol="make-contact",
    )


def test_chain_entries_are_stored_sorted_by_index() -> None:
    """`Chain.entries` is ordered by `index`, whatever order it was constructed in."""
    first = ChainEntry(function=function_id("a"), index=0)
    second = ChainEntry(function=function_id("b"), index=1)
    assert _chain(second, first).entries == (first, second)


def test_chain_with_a_duplicate_index_is_a_schema_error() -> None:
    """Two entries with the same `index` cannot be ordered, so construction raises."""
    with pytest.raises(SchemaError):
        _chain(
            ChainEntry(function=function_id("a"), index=0),
            ChainEntry(function=function_id("b"), index=0),
        )


def test_chain_with_a_repeated_function_is_a_schema_error() -> None:
    """One function cannot sit at two places of the same series chain."""
    with pytest.raises(SchemaError):
        _chain(
            ChainEntry(function=function_id("a"), index=0),
            ChainEntry(function=function_id("a"), index=1),
        )


def test_symbol_choice_with_one_selector_is_accepted() -> None:
    """A choice selecting by `kind` alone constructs."""
    assert _choice(function=False, kind=True).kind is FunctionKind.CONTACT_NO


def test_symbol_choice_selecting_by_template_alone_is_accepted() -> None:
    """A choice selecting by `template` alone constructs (model-0030)."""
    choice = _choice(function=False, kind=False, template=True)
    assert choice.template == template_id("t")
    assert choice.function is None
    assert choice.part is None
    assert choice.kind is None


def test_symbol_choice_with_two_selectors_is_a_schema_error() -> None:
    """Setting both `function` and `kind` is ambiguous, so construction raises."""
    with pytest.raises(SchemaError):
        _choice(function=True, kind=True)


def test_symbol_choice_with_function_and_template_is_a_schema_error() -> None:
    """Setting both `function` and `template` is ambiguous, so construction raises."""
    with pytest.raises(SchemaError):
        _choice(function=True, kind=False, template=True)


def test_symbol_choice_with_no_selector_is_a_schema_error() -> None:
    """A choice that selects nothing raises."""
    with pytest.raises(SchemaError):
        _choice(function=False, kind=False)


def test_order_hint_between_a_group_and_itself_is_a_schema_error() -> None:
    """`before == after` orders nothing, so construction raises."""
    group = Id(kind="aspect_node", value="3" * 32)
    with pytest.raises(SchemaError):
        OrderHint(
            id=Id(kind="layout.order_hint", value="4" * 32),
            key=("examples", "layout", "order"),
            before=group,
            after=group,
        )
