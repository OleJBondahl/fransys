"""The order gate's scanners on synthetic source (spec NUMBER-SORT K13); no file is read."""

import ast

import pytest
from gate_scan import src_modules
from order_sites_scan import (
    callable_param_orders,
    core_order_sites,
    core_text_keys,
    order_id_reads,
    order_sites,
)
from test_one_home import (
    GROUPERS,
    SCANNERS,
    Sites,
    compare,
    load_allowlist,
    scan,
)

REPORTS = "fransys_reports.x"
DERIVE_ROWS = "fransys_model.derive.rows"
DESIGNATION_IMPORT = "from fransys_model.derive.order import designation_key\n"
SORTS_BY_DESIGNATION = (
    "from .order import designation_key\n"
    "def f(m, xs):\n    return sorted(xs, key=designation_key)\n"
)


def _sites(scanner, source, module):
    return scan(scanner, source, module)


SITE_KINDS = [
    "return sorted(xs)",
    "return reversed(xs)",
    "xs.sort()",
    "xs.reverse()",
    "return heapq.nsmallest(2, xs)",
    "return xs[::-1]",
    "return max(xs, key=len)",
    'return min("a", b)',
    'return min(f"{a}", b)',
    "return min(str(a), b)",
    "for x in set(xs): pass",
    "return [x for x in frozenset(xs)]",
    "for x in {1, 2}: pass",
]


@pytest.mark.parametrize("stmt", SITE_KINDS)
def test_each_site_kind_is_an_order_site(stmt):
    source = f"def f(xs):\n    {stmt}\n"
    assert _sites(order_sites, source, REPORTS) == {"fransys_reports.x::f": [2]}


def test_a_method_reverse_in_the_model_is_a_site_outside_a_home():
    source = "def f(xs):\n    xs.reverse()\n"
    assert _sites(order_sites, source, "fransys_model.derive.x") == {
        "fransys_model.derive.x::f": [2]
    }


def test_plain_min_max_and_model_set_loop_are_not_sites():
    assert _sites(order_sites, "def f(a, b):\n    return min(1, 2), max(a, b)\n", REPORTS) == {}
    source = "def f(xs):\n    for x in set(xs): pass\n"
    assert _sites(order_sites, source, "fransys_model.derive.x") == {}


@pytest.mark.parametrize(
    "source",
    [
        SORTS_BY_DESIGNATION,
        (
            "from fransys_model.derive.order import designation_key\n"
            "def f(m, xs):\n    return sorted(xs, key=designation_key)\n"
        ),
        (
            "from fransys_model.kernel import natural_key\n"
            "def f(xs):\n    return sorted(xs, key=natural_key)\n"
        ),
        (
            "from fransys_model.derive import order\n"
            "def f(m, xs):\n    return sorted(xs, key=order.designation_key)\n"
        ),
    ],
    ids=["relative", "absolute", "natural_key", "attribute"],
)
def test_a_home_key_by_name_is_allowed_in_the_model(source):
    assert _sites(order_sites, source, DERIVE_ROWS) == {}


def test_the_same_home_import_is_a_site_outside_the_model():
    source = DESIGNATION_IMPORT + "def f(m, xs):\n    return sorted(xs, key=designation_key)\n"
    assert _sites(order_sites, source, REPORTS) == {"fransys_reports.x::f": [3]}


def test_a_non_home_key_in_the_model_is_a_site():
    lam = (
        DESIGNATION_IMPORT
        + "def f(m, xs):\n    return sorted(xs, key=lambda i: designation_key(m, i))\n"
    )
    assert _sites(order_sites, lam, DERIVE_ROWS) == {"fransys_model.derive.rows::f": [3]}

    local_def = (
        DESIGNATION_IMPORT
        + "def f(m, xs):\n"
        + "    def k(i):\n"
        + "        return designation_key(m, i)\n"
        + "    return sorted(xs, key=k)\n"
    )
    assert _sites(order_sites, local_def, DERIVE_ROWS) == {"fransys_model.derive.rows::f": [5]}

    tuple_key = (
        DESIGNATION_IMPORT + "def f(m, xs):\n    return sorted(xs, key=(designation_key, 1))\n"
    )
    assert _sites(order_sites, tuple_key, DERIVE_ROWS) == {"fransys_model.derive.rows::f": [3]}

    no_key = "def f(xs):\n    return sorted(xs)\n"
    assert _sites(order_sites, no_key, DERIVE_ROWS) == {"fransys_model.derive.rows::f": [2]}


HOME_MODULES = [
    "fransys_model.derive.order",
    "fransys_model.derive.order_lists",
    "fransys_kernel.canonical_forms",
    "fransys_kernel.diff",
    "fransys_kernel.findings",
    "fransys_kernel.naturals",
    "fransys_layout.core.keys",
]


@pytest.mark.parametrize("module", HOME_MODULES)
def test_the_homes_are_not_scanned(module):
    source = "def f(xs):\n    return sorted(xs, key=lambda i: i)\n"
    assert _sites(order_sites, source, module) == {}


def test_core_order_sites_scans_only_the_core():
    source = "def f(xs):\n    return sorted(xs)\n"
    assert _sites(core_order_sites, source, "fransys_layout.core.keys") == {
        "fransys_layout.core.keys::f": [2]
    }
    assert _sites(core_order_sites, source, REPORTS) == {}
    home_key = DESIGNATION_IMPORT + "def f(m, xs):\n    return sorted(xs, key=designation_key)\n"
    assert _sites(core_order_sites, home_key, "fransys_layout.core.keys") == {
        "fransys_layout.core.keys::f": [3]
    }


CORE = "fransys_layout.core.k"


def test_core_text_keys_counts_natural_key_and_str_methods():
    natural = "def f(xs):\n    return sorted(xs, key=lambda b: natural_key(b.id))\n"
    assert _sites(core_text_keys, natural, CORE) == {"fransys_layout.core.k::f": [2]}

    lower = "def f(xs):\n    return sorted(xs, key=lambda s: s.lower())\n"
    assert _sites(core_text_keys, lower, CORE) == {"fransys_layout.core.k::f": [2]}

    # the re.sub attribute, then its two string literals "a" and "b"
    regex = 'def f(xs):\n    return sorted(xs, key=lambda s: re.sub("a", "b", s))\n'
    assert _sites(core_text_keys, regex, CORE) == {"fransys_layout.core.k::f": [2, 2, 2]}

    literal = 'def f(xs):\n    return sorted(xs, key=lambda s: (s.rank, "x"))\n'
    assert _sites(core_text_keys, literal, CORE) == {"fransys_layout.core.k::f": [2]}

    none = "def f(xs):\n    return sorted(xs, key=lambda b: (b.y, b.x))\n"
    assert _sites(core_text_keys, none, CORE) == {}


def test_core_text_keys_follows_a_named_key_def_and_ignores_other_modules():
    named = "def k(s):\n    return s.lower()\ndef f(xs):\n    return sorted(xs, key=k)\n"
    assert _sites(core_text_keys, named, CORE) == {"fransys_layout.core.k::f": [2]}
    lower = "def f(xs):\n    return sorted(xs, key=lambda s: s.lower())\n"
    assert _sites(core_text_keys, lower, REPORTS) == {}


ORDER = "fransys_model.derive.order"


def test_order_id_reads_finds_an_id_read_in_a_tie():
    source = "def plc_channel_tie(number, function):\n    return number, function.id\n"
    assert _sites(order_id_reads, source, ORDER) == {f"{ORDER}::plc_channel_tie": [2]}


def test_order_id_reads_finds_a_bare_id_tuple_element_in_a_key_lambda():
    source = (
        "def in_designation_order(model, listed):\n"
        "    return sorted(listed, key=lambda item: (designation_key(model, item), item))\n"
    )
    assert _sites(order_id_reads, source, ORDER) == {f"{ORDER}::in_designation_order": [2]}


def test_order_id_reads_needs_an_id_read_and_the_home_module():
    no_id = "def f(xs):\n    return sorted(xs, key=lambda i: i.rank)\n"
    assert _sites(order_id_reads, no_id, ORDER) == {}
    tie = "def plc_channel_tie(number, function):\n    return number, function.id\n"
    assert _sites(order_id_reads, tie, "fransys_model.derive.other") == {}
    assert _sites(order_id_reads, tie, "fransys_model.derive.order_lists") == {
        "fransys_model.derive.order_lists::plc_channel_tie": [2]
    }


SECTIONS = ("order_sites", "core_order_sites", "core_text_keys", "order_id_reads")


@pytest.fixture(scope="module")
def tree_sites() -> dict[str, Sites]:
    """Each gate section's sites over the tree, with every file parsed once for the module."""
    trees = [
        (module, ast.parse(path.read_text(encoding="utf-8"))) for module, path in src_modules()
    ]
    assert trees, "the source walk found no file"
    return {section: _sites_over(SCANNERS[section], trees) for section in SECTIONS}


def _sites_over(scanner, trees: list[tuple[str, ast.Module]]) -> Sites:
    """`scan_tree`'s grouping over trees parsed once, so each gate walk does not re-parse."""
    sites: Sites = {}
    for module, tree in trees:
        for name, line in scanner(tree, module):
            if scanner in GROUPERS:
                sites.setdefault(GROUPERS[scanner](module, name), []).append(f"{module}:{line}")
            else:
                sites.setdefault(f"{module}::{name}", []).append(line)
    return sites


def _problems(section: str, walked: dict[str, Sites]) -> list[str]:
    """`gate`'s problems for one section, over the sites the fixture already walked."""
    sites = walked[section]
    allowed = load_allowlist()[section]
    assert sites, f"the {section} walk found no site"
    assert allowed, f"[{section}] of one-home.toml is empty"
    return compare(sites, allowed)


def _rises(section: str, walked: dict[str, Sites]) -> list[str]:
    """The gate's problems for a table that may fall: only a rise counts."""
    return [p for p in _problems(section, walked) if not p.endswith("lower the allowlist")]


def test_no_sort_outside_the_order_homes(tree_sites):
    assert _problems("order_sites", tree_sites) == []


def test_the_layout_core_raw_sorts_do_not_rise(tree_sites):
    assert _rises("core_order_sites", tree_sites) == []


def test_the_layout_core_text_keys_only_fall(tree_sites):
    assert _problems("core_text_keys", tree_sites) == []


def test_no_order_key_of_the_home_reads_an_id_more_than_today(tree_sites):
    assert _rises("order_id_reads", tree_sites) == []


def test_the_order_gate_can_fail():
    sites = scan(order_sites, "def f(rows):\n    return sorted(rows)\n", "fransys_reports.x")
    assert compare(sites, {}) == [
        "fransys_reports.x::f read 1 times, allowed 0: fransys_reports.x:2"
    ]
    assert compare(sites, {"fransys_reports.x::f": 2}) == [
        "fransys_reports.x::f read 1 times, allowed 2: lower the allowlist"
    ]


def test_no_order_function_takes_a_key_or_rank_callable():
    found = {
        f"{module}::{name}"
        for module, path in src_modules()
        for name, _ in callable_param_orders(ast.parse(path.read_text(encoding="utf-8")), module)
    }
    assert found == set()


@pytest.mark.parametrize(
    "params", ["values, rank: Callable[[T], Any]", "values, *, key: 'Callable[[T], int] | None'"]
)
def test_an_order_function_with_a_callable_parameter_is_refused_by_name(params):
    source = f"def first_ranked({params}):\n    return min(values, key=rank)\n"
    tree = ast.parse(source)
    assert callable_param_orders(tree, "fransys_model.derive.order_kit") == [("first_ranked", 1)]
    assert callable_param_orders(tree, "fransys_model.derive.rows") == []
    plain = ast.parse("def first_device(devices, ranks: Mapping):\n    return devices\n")
    assert callable_param_orders(plain, "fransys_model.derive.order_kit") == []


ORDER_SIBLING = "fransys_model.derive.order_kit"


@pytest.mark.parametrize(
    "key", ["lambda f: f.origin", "lambda p: (p.upper, p.lower)", "lambda f: f.a.b"]
)
def test_an_order_sibling_sorting_by_an_attribute_lambda_is_a_site(key):
    source = f"def f(xs):\n    return sorted(xs, key={key})\n"
    assert _sites(order_sites, source, ORDER_SIBLING) == {f"{ORDER_SIBLING}::f": [2]}


@pytest.mark.parametrize("key", ["lambda f: g(f)", "lambda f: f.a()", "len"])
def test_an_order_sibling_with_another_key_is_no_site(key):
    source = f"def f(xs):\n    return sorted(xs, key={key})\n"
    assert _sites(order_sites, source, ORDER_SIBLING) == {}


def test_the_order_module_itself_may_sort_by_an_attribute_lambda():
    source = "def f(xs):\n    return sorted(xs, key=lambda f: f.origin)\n"
    assert _sites(order_sites, source, "fransys_model.derive.order") == {}
