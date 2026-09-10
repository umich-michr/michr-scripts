---
applyTo: "python/packages/program-configuration/**"
---

# program-configuration instructions

This reusable package owns layered, typed, secret-aware configuration
resolution.

Core precedence is:

```text
explicit → environment → dotenv → default → prompt → unresolved
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
- keep dotenv-file I/O explicit and separate from the pure core resolver;
- disable implicit dotenv interpolation;
- never mutate `os.environ`.
- prompting must be explicit and injectable;
- do not prompt when a higher-precedence source or default resolved the value;
- do not inspect terminal interactivity when no unresolved setting can prompt;
- secret prompts must use a non-echoing reader;
- batch consumers must be able to disable prompting;

Use synthetic values in tests. Never include real credentials, DSNs, tokens, orinstitutional configuration.
