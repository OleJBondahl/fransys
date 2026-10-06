import hashlib
import importlib.util
from pathlib import Path

import fransys_overview
import pytest
from fransys_overview import html
from fransys_overview._vendor_cytoscape import (
    CYTOSCAPE_MIN_JS,
    CYTOSCAPE_SHA256,
    CYTOSCAPE_VERSION,
)

PACKAGE = Path(fransys_overview.__file__).resolve().parent
SCRIPT = PACKAGE.parent.parent / "scripts" / "vendor_cytoscape.py"


def _script():
    spec = importlib.util.spec_from_file_location("vendor_cytoscape_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_constant_has_the_recorded_sha256():
    assert hashlib.sha256(CYTOSCAPE_MIN_JS.encode("utf-8")).hexdigest() == CYTOSCAPE_SHA256


def test_a_changed_constant_would_not_have_the_recorded_sha256():
    changed = CYTOSCAPE_MIN_JS.replace("function", "functio", 1)
    assert hashlib.sha256(changed.encode("utf-8")).hexdigest() != CYTOSCAPE_SHA256


def test_the_library_says_it_is_the_recorded_version():
    assert f'.version="{CYTOSCAPE_VERSION}"' in CYTOSCAPE_MIN_JS


def test_the_licence_ships_in_the_package():
    text = (PACKAGE / "LICENSE-cytoscape.txt").read_text(encoding="utf-8")
    assert text.startswith("Copyright (c) 2016-2026, The Cytoscape Consortium.")
    assert "Permission is hereby granted, free of charge" in text
    assert "THE SOFTWARE IS PROVIDED" in text


def test_the_page_carries_the_librarys_licence_banner(demo_cabinet):
    page = html(demo_cabinet)
    start = page.index("/**")
    banner = page[start : page.index("*/", start)]
    stripped = "\n".join(
        line.removeprefix(" * ").removeprefix(" *").rstrip() for line in banner.splitlines()[1:]
    )
    licence = (PACKAGE / "LICENSE-cytoscape.txt").read_text(encoding="utf-8")
    assert stripped.strip() == licence.strip()


def test_the_vendored_module_is_what_the_script_writes():
    module = _script()
    written = module._module(CYTOSCAPE_MIN_JS, CYTOSCAPE_VERSION, CYTOSCAPE_SHA256)
    assert (PACKAGE / "_vendor_cytoscape.py").read_text(encoding="utf-8") == written


AWKWARD_SOURCE = (
    "a \"double\" and 'single' quote, back\\slash, tab\t, newline\n, carriage\r, "
    "café, “quotes”, astral \U0001f600, control \x01, " + "x" * 400
)


def test_the_script_writes_module_text_that_reads_back_exactly():
    module = _script()
    text = module._module(AWKWARD_SOURCE, "1.2.3", "0" * 64)
    assert module._read_back(text) == AWKWARD_SOURCE
    assert text.isascii()
    assert "\r" not in text
    assert max(len(line) for line in text.splitlines()) <= module.MAX_LINE


def test_the_script_check_can_fail():
    module = _script()
    text = module._module(AWKWARD_SOURCE, "1.2.3", "0" * 64)
    tampered = text.replace("caf", "cof", 1)
    assert module._read_back(tampered) != AWKWARD_SOURCE


def test_the_script_refuses_the_wrong_number_of_arguments(capsys):
    assert _script().main([]) == 2
    assert "usage" in capsys.readouterr().out


@pytest.mark.parametrize("char", ["\\", '"', "'", "\n", "\r", "\t", "\x01", "é", "\U0001f600"])
def test_every_kind_of_character_is_escaped_to_ascii(char):
    module = _script()
    assert module._escape(char, '"').isascii()
