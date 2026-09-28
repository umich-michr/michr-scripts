# program-configuration

Reusable layered, typed, and secret-aware configuration resolution.

## Basic usage

```python
from pathlib import Path

from program_configuration import (
    SettingSpec,
    parse_boolean,
    parse_path,
    resolve_configuration,
)

configuration = resolve_configuration(
    (
        SettingSpec(
            name="input_path",
            environment_variable="EXAMPLE_INPUT",
            parser=parse_path,
            default=Path("input/data.csv"),
        ),
        SettingSpec(
            name="enabled",
            environment_variable="EXAMPLE_ENABLED",
            parser=parse_boolean,
            default=False,
        ),
    ),
    explicit={"input_path": None, "enabled": None},
    environment={"EXAMPLE_ENABLED": "true"},
    dotenv={},
)

assert configuration["enabled"] is True
```

## Resolution order

```text
explicit
→ process environment
→ dotenv
→ default
→ prompt
→ missing-setting error
```

Invalid values fail at the highest-precedence source; they do not fall through.

`None` is missing. Blank strings are missing by default. Set
`blank_is_missing=False` when blank is meaningful.

## Dotenv

Load explicitly:

```python
from program_configuration import load_dotenv_file

dotenv = load_dotenv_file(".env", required=False)
```

Loading does not mutate `os.environ`, and interpolation is disabled. The caller
supplies the actual process environment separately.

## Required and secret settings

A setting without a default is required. All unresolved names are reported
together in declaration order through `MissingConfigurationError`.

Mark sensitive values with `secret=True`. Secret values remain available to the
consumer but are redacted from representations and configuration errors.

## Prompting

Prompting is explicit and injectable.

```python
from program_configuration import TerminalPromptProvider

configuration = resolve_configuration(
    settings,
    environment=environment,
    dotenv=dotenv,
    prompt_provider=TerminalPromptProvider(),
    prompt_enabled=True,
)
```

Only unresolved settings with prompt text can prompt. Secret prompts do not echo.
Batch consumers can disable prompting.

## Public scope

The package owns:

- setting declarations;
- precedence and provenance;
- reusable parsers;
- explicit dotenv loading;
- injectable prompting;
- secret redaction.

It does not own program option names, argparse, database drivers, SQL semantics,
row sources, report generation, or application logging.

## Development

```bash
make test PACKAGE=program-configuration
make coverage PACKAGE=program-configuration
make check
```

## License

MIT
