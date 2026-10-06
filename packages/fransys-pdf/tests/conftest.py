import sys
from pathlib import Path

# --import-mode=importlib leaves the test directory off sys.path; tests import `_build` by
# name. Workspace rule: tests conftests append to sys.path, never insert(0) (see
# packages/fransys-model/tests/conftest.py).
sys.path.append(str(Path(__file__).parent))
