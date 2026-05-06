import logging
from unittest.mock import mock_open, patch

import pytest
import yaml  # type: ignore[import-untyped]

from core import config_loader


@pytest.fixture(autouse=True)
def _mock_dotenv():
    """Prevent load_dotenv from reading a real .env file in all tests."""
    with patch("core.config_loader.load_dotenv"):
        yield


# ─── load_config ────────────────────────────────────────────


def test_load_config_returns_dict():
    """load_config should parse valid YAML and return a dict."""
    yaml_content = "key: value\nnested:\n  inner: 42"
    with patch("builtins.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.exists", return_value=True):
        result = config_loader.load_config("fake_path.yaml")

    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["nested"]["inner"] == 42


def test_load_config_file_not_found_returns_empty():
    """load_config should return {} when the config file does not exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = config_loader.load_config("nonexistent.yaml")

    assert result == {}


def test_env_var_override():
    """An env var set via os.environ should replace ${VAR_NAME} in config."""
    yaml_content = "database_url: ${DB_URL}"
    with (
        patch("builtins.open", mock_open(read_data=yaml_content)),
        patch("pathlib.Path.exists", return_value=True),
        patch.dict("os.environ", {"DB_URL": "postgres://localhost:5432/mydb"}),
    ):
        result = config_loader.load_config("fake_path.yaml")

    assert result["database_url"] == "postgres://localhost:5432/mydb"


def test_load_config_yaml_parse_error():
    """load_config should raise yaml.YAMLError when YAML is malformed."""
    with (
        patch("builtins.open", mock_open(read_data="irrelevant")),
        patch("pathlib.Path.exists", return_value=True),
        patch("yaml.safe_load", side_effect=yaml.YAMLError("bad yaml")),
        pytest.raises(yaml.YAMLError),
    ):
        config_loader.load_config("fake_path.yaml")


# ─── _check_hardcoded_secrets ────────────────────────────────


def test_check_hardcoded_secrets_no_secrets(caplog):
    """No warning should be logged when values use env-var references (${...})."""
    config = {
        "api_key": "${API_KEY}",
        "secret": "${SECRET}",
        "normal_key": "normal_value",
    }
    with caplog.at_level(logging.WARNING):
        config_loader._check_hardcoded_secrets(config, config_path="test.yaml")

    assert "检测到硬编码密钥" not in caplog.text


def test_check_hardcoded_secrets_detects_api_key(caplog):
    """A warning should be logged when a sensitive key has a plaintext value."""
    config = {"openai": {"api_key": "sk-1234567890abcdef"}}
    with caplog.at_level(logging.WARNING):
        config_loader._check_hardcoded_secrets(config, config_path="test.yaml")

    assert "检测到硬编码密钥" in caplog.text
    # The warning should include the path to the offending key
    assert "test.yaml" in caplog.text
    assert "openai.api_key" in caplog.text
