"""Gør det muligt at køre "python -m fodbold"."""

import sys

from fodbold.cli import main

sys.exit(main())
