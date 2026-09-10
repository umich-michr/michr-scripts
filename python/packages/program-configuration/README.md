# program-configuration

Reusable layered, typed, and secret-aware configuration resolution for runnable
programs.

## Scope

The package resolves settings declared by a consuming program.

Core precedence:

```text
explicit value
→ process environment
→ dotenv mapping
→ default
→ unresolved
```

The core resolver is pure: callers supply mappings. An explicit dotenv loader
is available for consumers that need file-based local configuration.

The package does not inspect or mutate `os.environ`, parse command lines, or
prompt implicitly.

The package does not own:

- application-specific option names;
- `argparse` parsers;
- database drivers or credentials;
- SQL bind semantics;
- row-source construction;
- report behavior;
- logging configuration.

## Example

```python
from pathlib import Path

from program_configuration import (
    SettingSpec,
    parse_boolean,
    parse_path,
    resolve_configuration,
)

settings = (
    SettingSpec(
        name="schema_path",
        environment_variable="EXAMPLE_SCHEMA",
        parser=parse_path,
        default=Path("input/schema.json"),
    ),
    SettingSpec(
        name="include_text",
        environment_variable="EXAMPLE_INCLUDE_TEXT",
        parser=parse_boolean,
        default=False,
    ),
)

configuration = resolve_configuration(
    settings,
    explicit={
        "schema_path": None,
        "include_text": None,
    },
    environment={
        "EXAMPLE_INCLUDE_TEXT": "true",
    },
    dotenv={
        "EXAMPLE_SCHEMA": "local-schema.json",
    },
)

assert configuration["schema_path"] == Path("local-schema.json")
assert configuration["include_text"] is True
```

## Dotenv files

Load a dotenv file explicitly:

```python
from program_configuration import load_dotenv_file

dotenv = load_dotenv_file(
    ".env",
    required=False,
)
```

A missing optional file returns an empty mapping. A missing required file raises
`DotenvFileError`.

Loading does not mutate `os.environ`, and variable interpolation is disabled.
The consuming program remains responsible for supplying the real process
environment separately:

```python
import os

configuration = resolve_configuration(
    settings,
    environment=os.environ,
    dotenv=dotenv,
)
```

This preserves the precedence:

```text
explicit → process environment → dotenv → default
```


## Missing values

A setting without a default is required when no higher-precedence source
supplies a value:

```python
SettingSpec(
    name="input_path",
    environment_variable="EXAMPLE_INPUT",
    parser=parse_path,
)
```

All unresolved setting names are reported together in declaration order through
`MissingConfigurationError`.

`None` is treated as missing. By default, blank strings are also treated as
missing and permit fallback to a lower-precedence source.

Set:

```python
blank_is_missing = False
```

when a blank string is a meaningful raw value.

## Secret values

Mark a setting as secret:

```python
SettingSpec(
    name="password",
    environment_variable="EXAMPLE_PASSWORD",
    parser=parse_nonblank_string,
    secret=True,
)
```

Resolved secret values are available to the consuming program, but are redacted
from `ResolvedValue` and `ResolvedConfiguration` representations.

Errors identify the setting and source without including the raw value.

## Provenance

```python
from program_configuration import ValueSource

assert configuration.source_for("schema_path") is ValueSource.DOTENV
```

Supported sources are:

- `EXPLICIT`
- `ENVIRONMENT`
- `DOTENV`
- `DEFAULT`

## Parsers

The package exports reusable parsers for:

- nonblank strings;
- Booleans;
- integers;
- positive integers;
- paths;
- JSON objects.

Parsers validate untrusted values and raise `ValueError` when conversion fails.

## Planned next increment

The next increment will add:

- injected prompt providers;
- secret prompts through `getpass`;
- noninteractive behavior;
- resolution of otherwise missing settings through prompts.

Prompting will occur only after explicit values, the process environment,
dotenv values, and defaults have been considered.

## Development

Run from the repository root:

```bash
make test PACKAGE=program-configuration
make coverage PACKAGE=program-configuration
make check
```

## License

MIT
