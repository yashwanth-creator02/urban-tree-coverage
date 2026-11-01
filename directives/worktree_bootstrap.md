# Directive: Worktree Bootstrap & Environment Setup

## Purpose
Ensures git worktrees possess the necessary gitignored runtime environment, port bindings, and directory structure.

## Procedure
1. Execute `python execution/setup_worktree.py`
2. Check `.dev-port` allocation to verify port collision avoidance.
3. Validate presence of `.tmp/` intermediate scratch directory.
