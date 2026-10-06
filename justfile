# Windows runs recipes in PowerShell, so no `sh` is needed on PATH; Linux keeps its default shell
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# decision 0013's 6 workers locally; a CI runner sets PYTEST_WORKERS
pytest_workers := env_var_or_default("PYTEST_WORKERS", "6")

check:
    uv run ruff check .
    uv run ruff format --check .
    # ty keyed by the cwd's real case (LEAN LC5), resolved in Python so no recipe needs sh
    uv run python scripts/ty_check.py

# dead code sweep: confidence 60 for every package, whitelist.py fed to every line (decision 0050)
dead-code:
    uv run vulture packages/fransys-model/src whitelist.py --min-confidence 60
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
    uv run python packages/electrical-symbols/scripts/build.py

# the full suite; electrical-symbols, fransys-model, fransys-layout, fransys-parts,
# fransys-author and the reports, kicad, wago, overview and pdf output packages and
# the fransys facade are measured in the same run and have no gate
cov:
    uv run pytest -n {{pytest_workers}} --dist worksteal --cov=electrical_symbols --cov=fransys_model --cov=fransys_layout --cov=fransys_parts --cov=fransys_author --cov=fransys_reports --cov=fransys_kicad --cov=fransys_wago --cov=fransys_overview --cov=fransys_pdf --cov=fransys_render --cov=fransys --cov-report=term-missing --cov-report=json:.fransys/coverage.json --durations=20

ci: check dead-code cov
    uv run python scripts/cov_floors.py check .fransys/coverage.json coverage-floors.toml
    uv run python scripts/lean_check.py hard
    uv run python scripts/lean_check.py enforce
    uv run python scripts/lean_check.py report

fmt:
    uv run ruff format .
    uv run ruff check --fix .

# tests only, in parallel; ARGS narrows them (paths, -k, ...). Set PYTEST_WORKERS=4 when three or more
# test jobs run at once (owner 2026-09-26)
test *ARGS:
    uv run pytest -n {{pytest_workers}} --dist worksteal {{ARGS}}

# rewrite the tracked model and layout goldens on a work branch, then their diff stat; refused on main (decision 0101)
regen-goldens *PKG:
    uv run python scripts/regen_goldens.py {{PKG}}

# just api PACKAGE: prints one package's API surface, built on demand, never stored (MS9,
# decision 0053) -- read this before another package's source, per root CLAUDE.md
api PACKAGE:
    uv run python scripts/lean_api.py {{PACKAGE}}

# the docs site (decision 0105, experimental): stages into .fransys/site-src/, builds strict into .fransys/site/
site EXAMPLES_DIR:
    uv run --group site python scripts/build_site.py {{EXAMPLES_DIR}}

# the maintainers' own recipes live in internal/; the public export leaves that folder out (PM12)
import? 'internal/internal.just'
