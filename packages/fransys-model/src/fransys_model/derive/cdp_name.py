"""The CDP spelling of a signal name: the one home of what the WAGO file writes and PLC_SIGNAL_NAME_TWICE compares (wago-0002)."""

import re


def cdp_name(text: str) -> str:
    """`text` as a CDP name: `[A-Za-z0-9_]` only, no `_` run or edge, `N_` before a first digit; `""` when nothing is left.

    Every other character, a non-ASCII letter too, is dropped as a separator. "Door" and "Door!" are one CDP name.
    """
    name = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", text)).strip("_")
    return f"N_{name}" if name[:1].isdigit() else name
