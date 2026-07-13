#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from devflow_launcher import export_or_run

export_or_run('render_setup_report', globals(), __name__)
