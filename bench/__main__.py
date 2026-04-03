"""Allow running as: python -m bench"""
import sys
from .cli import main

try:
    main()
except SystemExit as e:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(e.code)
