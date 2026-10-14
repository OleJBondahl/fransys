"""The page template and how it is filled (decisions overview-0001 and overview-0002)."""

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# Named tokens are `@@NAME@@`. The style and the frame are written out here; the library, the data
# and the script are the values filled in. The page names no `src`, and an `href` only in script.
TEMPLATE: Final[str] = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<style>
:root { --bg: #ffffff; --fg: #1c2b39; --muted: #5b6b7a; --panel: #f4f6f8; --border: #c3ccd5;
  --accent: #d9480f; --line: #4b5966; }
:root[data-theme="dark"] { --bg: #262b33; --fg: #e6ebf0; --muted: #a3afbb; --panel: #2e343d;
  --border: #46505c; --accent: #ff9a5c; --line: #b4bfca; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #262b33; --fg: #e6ebf0; --muted: #a3afbb;
    --panel: #2e343d; --border: #46505c; --accent: #ff9a5c; --line: #b4bfca; }
}
html, body { height: 100%; margin: 0; }
body { display: flex; flex-direction: column; background: var(--bg); color: var(--fg);
  font: 14px/1.4 system-ui, sans-serif; }
header { position: relative; display: flex; flex-wrap: wrap; align-items: center;
  gap: 6px 14px; padding: 6px 12px;
  background: var(--panel); border-bottom: 1px solid var(--border); }
h1 { margin: 0; font-size: 17px; }
label.pick { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; }
select, input, button { background: var(--bg); color: var(--fg); border: 1px solid var(--border);
  border-radius: 3px; padding: 3px 6px; font: inherit; }
button { cursor: pointer; }
#features { font-size: 12px; }
#features summary { cursor: pointer; }
#feat-body { position: absolute; z-index: 6; top: 100%; min-width: 200px;
  padding: 6px 10px;
  background: var(--bg); border: 1px solid var(--border); }
#feat-body label { display: block; white-space: nowrap; }
#feat-body fieldset { margin: 6px 0 0; padding: 2px 6px; border: 1px solid var(--border); }
input[type="checkbox"]:disabled { appearance: none; width: 12px; height: 12px; margin: 0 4px 0 0;
  padding: 0; border: 1px solid var(--muted); border-radius: 2px; background: var(--panel);
  opacity: 0.6; cursor: not-allowed; }
input[type="checkbox"]:disabled:checked { background: var(--muted);
  box-shadow: inset 0 0 0 2px var(--panel); }
#find { position: relative; }
#search { width: 220px; }
#hits { position: absolute; z-index: 5; left: 0; right: 0; margin: 0; padding: 0; list-style: none;
  background: var(--bg); border: 1px solid var(--border); max-height: 240px; overflow: auto; }
#hits:empty { display: none; }
#hits li { padding: 3px 8px; cursor: pointer; }
#hits li:hover, #hits li[aria-selected="true"] { background: var(--panel); }
#bar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; padding: 4px 12px;
  border-bottom: 1px solid var(--border); font-size: 12px; }
#crumbs button { border: 0; background: none; color: var(--accent); padding: 0 2px; }
#crumbs span.here { font-weight: 600; }
.chip { display: inline-flex; gap: 4px; align-items: center; border: 1px solid var(--border);
  border-radius: 10px; padding: 0 8px; background: var(--panel); }
.chip button { border: 0; background: none; padding: 0; }
main { display: flex; flex: 1; min-height: 0; }
#tree { width: 230px; overflow: auto; padding: 6px 8px; border-right: 1px solid var(--border);
  background: var(--panel); font-size: 12px; }
#tree ul { list-style: none; margin: 0; padding-left: 14px; }
#tree summary { cursor: pointer; }
#stage { flex: 1; min-width: 0; display: flex; flex-direction: column; }
#legend { display: flex; flex-wrap: wrap; gap: 4px 12px; padding: 4px 12px; font-size: 12px; }
#legend[hidden] { display: none; }
#legend button { display: inline-flex; align-items: center; gap: 5px; border: 0; background: none;
  padding: 0 2px; }
#legend button.off { opacity: 0.4; text-decoration: line-through; }
#legend i { display: inline-block; width: 12px; height: 12px; border: 2px solid;
  border-radius: 2px; }
#cy { flex: 1; min-height: 0; }
#alt { flex: 1; min-height: 0; overflow: auto; padding: 8px 12px; }
#alt[hidden] { display: none; }
#alt h2 { margin: 12px 0 6px; font-size: 14px; }
#alt table { border-collapse: collapse; font-size: 12px; }
#alt th, #alt td { border: 1px solid var(--border); padding: 2px 6px; text-align: left; }
#alt td button { width: 100%; }
#alt td.cell { text-align: center; }
#alt ul { margin: 0; padding-left: 18px; }
#detail { width: 280px; overflow: auto; padding: 8px 12px; border-left: 1px solid var(--border);
  background: var(--panel); font-size: 12px; }
#detail h2 { margin: 0 0 6px; font-size: 14px; }
#detail p { margin: 0 0 6px; }
#members, #boxlist { margin: 0; padding: 0; list-style: none; }
#members button, #boxlist button { width: 100%; text-align: left; margin-bottom: 2px; }
#opens button { margin: 0 4px 4px 0; }
.sr { position: absolute; left: -9999px; }
@media print {
  header, #bar, #tree, #detail, #legend, #features { display: none; }
  #cy { height: 100vh; }
}
</style>
</head>
<body>
<header>
<h1>@@TITLE@@</h1>
<div id="find"><input id="search" type="search" role="combobox" aria-expanded="false"
  aria-controls="hits" placeholder="Find an item by designation"
  aria-label="Find an item by designation" autocomplete="off">
<ul id="hits" role="listbox"></ul></div>
<label class="pick">Colour by <select id="split"></select></label>
<label class="pick">View <select id="mode"></select></label>
<label class="pick">Theme <select id="theme"><option value="system">System</option>
<option value="light">Light</option><option value="dark">Dark</option></select></label>
<details id="features"><summary>Features</summary><div id="feat-body"></div></details>
<button id="up" type="button">Up one level</button>
<button id="png" type="button">Save PNG</button>
</header>
<div id="bar"><nav id="crumbs" aria-label="Levels"></nav><span id="opens"></span>
<span id="chips"></span></div>
<main>
<aside id="tree" aria-label="Parts"></aside>
<div id="stage"><div id="legend" aria-label="Legend"></div><div id="cy"></div>
<div id="alt" hidden></div></div>
<aside id="detail" aria-live="polite"></aside>
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
