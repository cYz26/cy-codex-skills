#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from devflow_launcher import export_or_run

export_or_run('inspect_repo', globals(), __name__)
