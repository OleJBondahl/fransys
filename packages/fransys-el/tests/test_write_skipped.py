"""`skipped_findings` (model-0314): one finding per `Skipped`, at its code's registered level."""

import pytest
from fransys_el import ProblemError, Skipped, skipped_findings
from fransys_el.placement_skips import (
    FUNCTION_WITHOUT_SYMBOL,
    NET_UNDER_TWO_DRAWN_PINS,
    NOT_SERIES_PARALLEL,
)
from placement_fixtures import planted_model

from fransys_model.derive import function_designation, port_designation
from fransys_model.kernel import Severity, render_id
from fransys_model.vocab import functions, ports


def test_a_function_without_symbol_is_a_warning_and_a_net_under_two_pins_a_warning() -> None:
    model = planted_model()
    function = next(iter(functions(model)))
    port = next(iter(ports(model)))
    found = skipped_findings(
        model,
        [
            Skipped("function", render_id(function), FUNCTION_WITHOUT_SYMBOL),
            Skipped("net", port.value, NET_UNDER_TWO_DRAWN_PINS),
        ],
    )
    assert [(f.code, f.severity) for f in found] == [
        ("FUNCTION_NOT_DRAWN", Severity.WARNING),
        ("NET_NOT_DRAWN", Severity.WARNING),
    ]
    assert [f.subjects for f in found] == [(function,), (port,)]
    assert FUNCTION_WITHOUT_SYMBOL in found[0].message
    assert NET_UNDER_TWO_DRAWN_PINS in found[1].message
    assert port_designation(model, port) in found[1].message
    assert found[1].fix
    assert "second drawn pin" in found[1].fix


def test_a_skipped_the_model_does_not_hold_is_refused() -> None:
    with pytest.raises(ProblemError, match="skipped function"):
        skipped_findings(
            planted_model(), [Skipped("function", "function:nope", FUNCTION_WITHOUT_SYMBOL)]
        )


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_bridge_is_one_warning_naming_each_of_its_functions() -> None:
    """Catches a bridge dropped silently, or named by its first function only."""
    model = planted_model()
    first, second = list(functions(model))[:2]
    skipped = Skipped("region", render_id(first), NOT_SERIES_PARALLEL, (render_id(second),))
    (found,) = skipped_findings(model, [skipped])
    assert (found.code, found.severity) == ("NOT_SERIES_PARALLEL", Severity.WARNING)
    assert found.subjects == (first, second)
    assert function_designation(model, first) in found.message
    assert function_designation(model, second) in found.message
    assert "d.series" in found.fix


def test_an_unwired_function_is_a_warning_naming_it_and_a_second_pin_is_not_asked() -> None:
    from fransys_el.placement_skips import FUNCTION_UNWIRED

    from fransys_model.derive import function_designation

    model = planted_model()
    function = next(iter(functions(model)))
    (found,) = skipped_findings(model, [Skipped("function", render_id(function), FUNCTION_UNWIRED)])
    assert (found.code, found.severity) == ("FUNCTION_NOT_WIRED", Severity.WARNING)
    assert found.subjects == (function,)
    assert function_designation(model, function) in found.message
