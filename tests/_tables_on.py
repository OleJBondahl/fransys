"""Settings with the contact tables switched on (CONTACT-TABLE): table tests build with these."""

from pathlib import Path

import fransys as fr

TABLES_ON = fr.settings(Path(__file__).with_name("tables_on.toml"))
