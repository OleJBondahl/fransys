"""The page colour table (O10): Paul Tol vibrant scheme, light and dark (overview-0002).

Colour scheme by Paul Tol (personal.sron.nl/~pault), BSD-3-Clause. A hue is darkened for the light
theme or lightened for the dark one until it passes 3:1 against the theme's background (WCAG
1.4.11); `tests/test_palette.py` computes that from this table.
"""

from typing import Any, Final

# Theme backgrounds, then (name, light value, dark value). Six hues, an alert red and a grey.
BACKGROUND: Final[dict[str, str]] = {"light": "#FFFFFF", "dark": "#262B33"}
HUES: Final[tuple[tuple[str, str, str], ...]] = (
    ("blue", "#0077BB", "#057ABC"),
    ("orange", "#E47231", "#EE7733"),
    ("teal", "#009988", "#009988"),
    ("magenta", "#EE3377", "#EE3377"),
    ("cyan", "#2B9DC8", "#33BBEE"),
    ("yellow", "#9F9235", "#CCBB44"),
)
ALERT: Final[tuple[str, str, str]] = ("red", "#CC3311", "#D04324")
NEUTRAL: Final[tuple[str, str, str]] = ("grey", "#929292", "#BBBBBB")


def palette_data() -> dict[str, Any]:
    """The table as the plain data the page reads."""
    return {
        "background": dict(BACKGROUND),
        "hues": [{"light": light, "dark": dark} for _, light, dark in HUES],
        "alert": {"light": ALERT[1], "dark": ALERT[2]},
        "neutral": {"light": NEUTRAL[1], "dark": NEUTRAL[2]},
    }
