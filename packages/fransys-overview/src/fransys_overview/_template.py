"""The page template and how it is filled (decision overview-0001)."""

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# Named tokens are `@@NAME@@`. The style is written out here; the library, the data and the
# script are the values that are filled in. There is no `src` or `href` anywhere.
TEMPLATE: Final[str] = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<style>
html, body { height: 100%; margin: 0; }
body { display: flex; flex-direction: column; color: #1c2b39;
  font: 14px/1.4 system-ui, sans-serif; }
header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding: 8px 12px;
  background: #eef2f6; border-bottom: 1px solid #b8c4d0; }
h1 { margin: 0; font-size: 18px; }
#search { width: 220px; padding: 4px 6px; }
#legend { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-left: auto; font-size: 12px; }
.key { display: inline-flex; align-items: center; gap: 5px; }
.key i { display: inline-block; width: 32px; border-top: 2px solid #555; }
.key i.cable { border-top-width: 5px; border-top-color: #333; }
.key i.mate { border-top-style: dotted; border-top-width: 3px; }
.key i.off { width: 22px; height: 12px; border: 1px dashed #4a6785; background: #dbe7f3;
  border-radius: 3px; }
main { display: flex; flex: 1; min-height: 0; }
#cy { flex: 1; min-width: 0; }
#detail { width: 280px; overflow: auto; padding: 8px 12px; border-left: 1px solid #b8c4d0;
  background: #f8fafc; font-size: 12px; }
#detail h2 { margin: 0 0 6px; font-size: 14px; }
#detail p { margin: 0 0 6px; }
</style>
</head>
<body>
<header>
<h1>@@TITLE@@</h1>
<input id="search" type="search" placeholder="Find an item by designation"
  aria-label="Find an item by designation" autocomplete="off">
<button id="reset" type="button">Reset view</button>
<div id="legend">
<span class="key"><i class="wire"></i>wire</span>
<span class="key"><i class="cable"></i>cable</span>
<span class="key"><i class="mate"></i>mate</span>
<span class="key"><i class="off"></i>not installed</span>
</div>
</header>
<main>
<div id="cy"></div>
<aside id="detail"></aside>
</main>
<script>@@CYTOSCAPE@@</script>
<script type="application/json" id="overview-data">@@DATA@@</script>
<script>@@APP@@</script>
</body>
</html>
"""

_TOKEN = re.compile(r"@@([A-Z]+)@@")


def fill(template: str, values: Mapping[str, str]) -> str:
    """`template` with each `@@NAME@@` filled from `values` in one pass (rules: README)."""
    tokens = set(_TOKEN.findall(template))
    if tokens != set(values):
        missing = sorted(tokens - set(values))
        unused = sorted(set(values) - tokens)
        msg = f"the template and the values disagree: no value for {missing}, no token for {unused}"
        raise ValueError(msg)
    return _TOKEN.sub(lambda match: values[match[1]], template)
