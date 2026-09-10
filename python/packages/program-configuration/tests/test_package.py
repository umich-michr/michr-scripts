"""Tests for the program-configuration package contract."""

from pathlib import Path

import program_configuration as package
from program_configuration import (
    MISSING,
    ConfigurationError,
    ConfigurationValueError,
    DotenvFileError,
    MissingConfigurationError,
    ResolvedConfiguration,
    ResolvedValue,
    SettingDefinitionError,
    SettingSpec,
    UnknownExplicitSettingError,
    ValueSource,
    load_dotenv_file,
    parse_boolean,
    parse_integer,
    parse_json_object,
    parse_nonblank_string,
    parse_path,
    parse_positive_integer,
    resolve_configuration,
)


def test_package_is_not_an_implicit_namespace() -> None:
    assert package.__file__ is not None


def test_package_exposes_version_and_typing_marker() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()


def test_public_api_exports_models() -> None:
    assert package.MISSING is MISSING
    assert package.SettingSpec is SettingSpec
    assert package.ResolvedValue is ResolvedValue
    assert package.ResolvedConfiguration is ResolvedConfiguration
    assert package.ValueSource is ValueSource


def test_public_api_exports_errors() -> None:
    assert package.ConfigurationError is ConfigurationError
    assert package.SettingDefinitionError is SettingDefinitionError
    assert package.ConfigurationValueError is ConfigurationValueError
    assert package.MissingConfigurationError is MissingConfigurationError
    assert package.UnknownExplicitSettingError is UnknownExplicitSettingError
    assert package.DotenvFileError is DotenvFileError


def test_public_api_exports_parsers() -> None:
    assert package.parse_nonblank_string is parse_nonblank_string
    assert package.parse_boolean is parse_boolean
    assert package.parse_integer is parse_integer
    assert package.parse_positive_integer is parse_positive_integer
    assert package.parse_path is parse_path
    assert package.parse_json_object is parse_json_object


def test_public_api_exports_dotenv_loader() -> None:
    assert package.load_dotenv_file is load_dotenv_file


def test_public_api_exports_resolver() -> None:
    assert package.resolve_configuration is resolve_configuration


def test_program_exceptions_share_one_base_class() -> None:
    assert issubclass(SettingDefinitionError, ConfigurationError)
    assert issubclass(ConfigurationValueError, ConfigurationError)
    assert issubclass(MissingConfigurationError, ConfigurationError)
    assert issubclass(UnknownExplicitSettingError, ConfigurationError)
    assert issubclass(ConfigurationError, ValueError)
