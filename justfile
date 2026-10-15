# Windows runs recipes in PowerShell, so no `sh` is needed on PATH; Linux keeps its default shell
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# 6 test workers locally; a CI runner sets PYTEST_WORKERS
pytest_workers := env_var_or_default("PYTEST_WORKERS", "6")

check:
    uv run ruff check .
    uv run ruff format --check .
    # ty keyed by the cwd's real case, resolved in Python so no recipe needs sh
    uv run python scripts/ty_check.py

# dead code sweep: confidence 60 for every package, whitelist.py fed to every line
dead-code:
    uv run vulture packages/fransys-model/src packages/fransys-kernel/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-layout/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-parts/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-reports/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-kicad/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-wago/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-overview/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-author/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-pdf/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys-render/src whitelist.py --min-confidence 60
    uv run vulture packages/electrical-symbols/src whitelist.py --min-confidence 60
    uv run vulture packages/fransys/src whitelist.py --min-confidence 60

# electrical-symbols: regenerate the tracked build/ and src/electrical_symbols/bundle.json
build-electrical-symbols:
    uv run python packages/electrical-symbols/scripts/write_version.py
    uv run symdef build packages/electrical-symbols

# the full suite; electrical-symbols, fransys-kernel, fransys-model, fransys-layout, fransys-parts,
# fransys-author and the reports, kicad, wago, overview and pdf output packages and
# the fransys facade are measured in the same run; each has a fixed 95% floor in coverage-floors.toml
cov:
    uv run pytest -n {{pytest_workers}} --dist worksteal --cov=electrical_symbols --cov=fransys_model --cov=fransys_kernel --cov=fransys_layout --cov=fransys_el --cov=fransys_parts --cov=fransys_author --cov=fransys_reports --cov=fransys_kicad --cov=fransys_wago --cov=fransys_overview --cov=fransys_pdf --cov=fransys_render --cov=fransys --cov-report=term-missing --cov-report=json:.fransys/coverage.json --durations=20

# the gates run side by side and print as blocks in this order: check, dead-code, cov, the coverage
# floors, lean hard, enforce, report (AW14); the exit code is the first failing gate's
ci:
    uv run python scripts/ci_gates.py

fmt:
    uv run ruff format .
    uv run ruff check --fix .

# tests only, in parallel, on a fresh AWS spot instance (decision 0134); ARGS narrows them (paths, -k, ...).
# No local fallback; PYTEST_WORKERS applies to the local `just ci` only
[positional-arguments]
test *ARGS:
    uv run python internal/scripts/aws_run.py run -- pytest -n auto --dist worksteal "$@"

# rewrite the tracked model and layout goldens on a work branch, then their diff stat; refused on main
regen-goldens *PKG:
    uv run python scripts/regen_goldens.py {{PKG}}

# just api PACKAGE: prints one package's API surface, built on demand, never stored;
# read this before another package's source
api PACKAGE:
    uv run python scripts/lean_api.py {{PACKAGE}}

# the docs site (experimental): stages into .fransys/site-src/, builds strict into .fransys/site/
site EXAMPLES_DIR:
    uv run --group site python scripts/build_site.py {{EXAMPLES_DIR}}

# the maintainers' own recipes live in internal/; the public export leaves that folder out (PM12)
import? 'internal/internal.just'
