"""Named exit codes for reflect commands.

Use these constants in new code instead of bare integers. Existing call sites
that already return 0/1 are left as-is until refined.

Conventions:
- 0  : success
- 1  : user error (bad args, missing file the user controls)
- 2  : environment error (missing tooling like `entire`/`git`/`qmd`, no .reflect/)
- 3  : upstream failure (Claude API/CLI failed, qmd index error)
"""

OK = 0
USER_ERROR = 1
ENV_ERROR = 2
UPSTREAM_ERROR = 3
