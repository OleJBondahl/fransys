"""The side order of an item box's pins (V1). Hit policy: rank key, the first criterion decides.

Each criterion ranks the subjects whose fact reads the preferred value first; the N/S cut and the
index grouping stay code at the site.
"""

from .rows import Criterion, Order

V1 = Order(
    "V1 side order",
    (
        Criterion("V1a", "power_function", prefer=True),
        Criterion("V1b", "takes_energy", prefer=True),
        Criterion("V1c", "ac_current", prefer=True),
    ),
)
