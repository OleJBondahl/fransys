"""Put the helper modules of this directory on the path (`--import-mode=importlib`)."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
