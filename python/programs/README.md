# Python programs

Runnable Python applications live under `python/programs/`.

Programs may compose reusable packages and own their command-line interface,
configuration, orchestration, logging, and external I/O.

## Programs

| Program | Purpose | Documentation |
|---|---|---|
| `study-posting-audit-report` | Normalize Study Posting Authoring audit rows from CSV or Oracle | [README](study-posting-audit-report/README.md) |
| `study-posting-audit-exploration` | Validate a normalized report and publish aggregate analysis and HTML | [README](study-posting-audit-exploration/README.md) |

For command examples, defaults, and end-to-end workflows, start with the
[Python workspace guide](../README.md).

## Boundary

Programs may depend on packages. Packages must not depend on programs. Shared
behavior belongs in an owning package instead of being copied between programs.

`tools/` is reserved for repository-maintenance utilities. User-facing or
operational applications belong here.
