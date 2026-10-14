"""PT3's short form and SI3's sheet texts: the pure parts of the page title (PAGES-TITLES)."""

import pytest

from fransys_model.derive import set_page_text, short_title


@pytest.mark.parametrize(
    ("entries", "short"),
    [
        (
            ("Relay and lamp circuit 1", "Relay and lamp circuit 2", "Relay and lamp circuit 3"),
            "Relay and lamp circuit 1 to 3",
        ),
        (
            ("Relay and lamp circuit 1", "Relay and lamp circuit 11"),
            "Relay and lamp circuit 1 to 11",
        ),
        (("Supply", "Mixer", "Pump 2"), "Supply to Pump 2"),
        (("-A1", "-B1", "-H1"), "-A1 to -H1"),
        (("Pump", "Pump 2"), "Pump to Pump 2"),
        (("Pump 1", "Pump"), "Pump 1 to Pump"),
        (("Pump 1",), None),
        (("Pump", "Pump"), None),
    ],
)
def test_the_short_form_prints_shared_leading_words_once(
    entries: tuple[str, ...], short: str | None
) -> None:
    assert short_title(entries) == short


def test_a_set_page_text_is_set_dot_page() -> None:
    assert set_page_text(2, 3) == "2.3"
