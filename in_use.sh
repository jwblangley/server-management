#!/usr/bin/env bash

# WARNING: This script is not necessarily entirely conclusive depending on your use case

# Number of users logged in (ssh or physical)
WHO="$(/usr/bin/who | /usr/bin/wc -l)"

# Are there tmux sessions (N.B: only for current user!)
/usr/bin/tmux list-sessions >/dev/null 2>&1
TMUX="$?"
TMUX="$((! TMUX))"

RESULT=$(( WHO || TMUX ))
# Negate for return code
RESULT="$((! RESULT))"
exit $RESULT
