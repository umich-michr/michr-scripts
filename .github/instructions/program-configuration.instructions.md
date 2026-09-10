---
applyTo: "python/packages/program-configuration/**"
---

# program-configuration instructions

This reusable package owns layered, typed, secret-aware configuration
resolution.

Core precedence is:

```text
explicit → environment → dotenv → default → unresolved
```

The package must remain independent of:

- specific runnable programs;
- argparse option definitions;
- database drivers;
- Oracle configuration;
- SQL bind semantics;
- row-source construction;
- report generation;
- application logging.

Rules:

- never mutate os.environ;
- never expose secret values in representations or errors;
- report all missing settings together;
- preserve setting declaration order;
- reject duplicate setting names;
- reject duplicate environment-variable names;
- validate all mappings at runtime;
- use injected prompt behavior when prompting is introduced;
- do not hide filesystem access in the pure core resolver.

Use synthetic values in tests. Never include real credentials, DSNs, tokens, orinstitutional configuration.
