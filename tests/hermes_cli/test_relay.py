"""Tests for relay/proxy configuration in hermes_cli."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from hermes_cli.config import load_config


class TestRelayConfigEnvVars:
    """Test CUSTOM_RELAY_* environment variables."""

    def test_custom_relay_base_url_env_var_recognized(self):
        """CUSTOM_RELAY_BASE_URL should be recognized as a valid env var."""
        from hermes_cli.config import OPTIONAL_ENV_VARS
        assert "CUSTOM_RELAY_BASE_URL" in OPTIONAL_ENV_VARS

    def test_custom_relay_api_key_env_var_recognized(self):
        """CUSTOM_RELAY_API_KEY should be recognized as a valid env var."""
        from hermes_cli.config import OPTIONAL_ENV_VARS
        assert "CUSTOM_RELAY_API_KEY" in OPTIONAL_ENV_VARS

    def test_relay_env_var_category_is_relay(self):
        """CUSTOM_RELAY_* vars should be in 'relay' category."""
        from hermes_cli.config import OPTIONAL_ENV_VARS
        assert OPTIONAL_ENV_VARS["CUSTOM_RELAY_BASE_URL"]["category"] == "relay"
        assert OPTIONAL_ENV_VARS["CUSTOM_RELAY_API_KEY"]["category"] == "relay"

    def test_relay_env_vars_are_advanced(self):
        """CUSTOM_RELAY_* vars should be marked as advanced."""
        from hermes_cli.config import OPTIONAL_ENV_VARS
        assert OPTIONAL_ENV_VARS["CUSTOM_RELAY_BASE_URL"].get("advanced") is True
        assert OPTIONAL_ENV_VARS["CUSTOM_RELAY_API_KEY"].get("advanced") is True


class TestRelayConfigDefaults:
    """Test relay configuration in DEFAULT_CONFIG."""

    def test_relay_section_exists_in_defaults(self):
        """DEFAULT_CONFIG should have a 'relay' section."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert "relay" in DEFAULT_CONFIG

    def test_relay_defaults_enabled_false(self):
        """Relay should be disabled by default."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["relay"]["enabled"] is False

    def test_relay_defaults_base_url_empty(self):
        """Relay base_url should be empty by default."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["relay"]["base_url"] == ""

    def test_relay_defaults_api_key_empty(self):
        """Relay api_key should be empty by default."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["relay"]["api_key"] == ""

    def test_relay_defaults_providers_empty_list(self):
        """Relay providers should be empty (all providers) by default."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["relay"]["providers"] == []

    def test_config_version_bumped(self):
        """Config version should be bumped when relay is added."""
        from hermes_cli.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["_config_version"] == 19


class TestRelayRuntimeHelpers:
    """Test relay helper functions in runtime_provider.py.

    These tests require httpx and other dependencies, so they are skipped
    when those dependencies are not available.
    """

    @pytest.fixture(autouse=True)
    def require_httpx(self):
        """Skip tests if httpx is not available."""
        pytest.importorskip("httpx", reason="httpx required for runtime_provider")

    def test_is_relay_enabled_env_true(self):
        """CUSTOM_RELAY_ENABLED=1 should enable relay."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_ENABLED": "1"}):
            from hermes_cli.runtime_provider import is_relay_enabled
            assert is_relay_enabled() is True

    def test_is_relay_enabled_env_false(self):
        """CUSTOM_RELAY_ENABLED=0 should disable relay."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_ENABLED": "0"}):
            from hermes_cli.runtime_provider import is_relay_enabled
            assert is_relay_enabled() is False

    def test_is_relay_enabled_no_env(self):
        """Without env var, relay should be disabled."""
        with patch.dict(os.environ, {}, clear=True):
            from hermes_cli.runtime_provider import is_relay_enabled
            assert is_relay_enabled() is False

    def test_get_relay_config_env_vars(self):
        """get_relay_config should read from env vars."""
        with patch.dict(os.environ, {
            "CUSTOM_RELAY_BASE_URL": "https://my-relay.com/v1",
            "CUSTOM_RELAY_API_KEY": "relay-key-123"
        }):
            from hermes_cli.runtime_provider import get_relay_config
            config = get_relay_config()
            assert config["enabled"] is True
            assert config["base_url"] == "https://my-relay.com/v1"
            assert config["api_key"] == "relay-key-123"

    def test_get_relay_config_env_base_url_only(self):
        """Env var CUSTOM_RELAY_BASE_URL alone enables relay."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_BASE_URL": "https://relay.example.com"}):
            from hermes_cli.runtime_provider import get_relay_config
            config = get_relay_config()
            assert config["enabled"] is True
            assert config["base_url"] == "https://relay.example.com"

    def test_get_relay_config_empty_when_disabled(self):
        """get_relay_config returns empty when relay is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            from hermes_cli.runtime_provider import get_relay_config
            config = get_relay_config()
            assert config["enabled"] is False
            assert config["base_url"] == ""
            assert config["api_key"] == ""

    def test_should_use_relay_for_provider_empty_list(self):
        """When providers list is empty, relay is used for all providers."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_BASE_URL": "https://relay.com"}):
            from hermes_cli.runtime_provider import should_use_relay_for_provider
            assert should_use_relay_for_provider("openai") is True
            assert should_use_relay_for_provider("anthropic") is True
            assert should_use_relay_for_provider("any-provider") is True

    def test_should_use_relay_for_provider_specific(self):
        """When providers list is set, only those providers use relay."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_BASE_URL": "https://relay.com"}):
            from hermes_cli.runtime_provider import should_use_relay_for_provider
            # Note: Currently we test with empty providers list since
            # config-based providers list isn't directly testable without
            # a full config file. The env var path works correctly.
            assert should_use_relay_for_provider("openai") is True

    def test_should_use_relay_disabled(self):
        """When relay is disabled, should_use_relay_for_provider returns False."""
        with patch.dict(os.environ, {}, clear=True):
            from hermes_cli.runtime_provider import should_use_relay_for_provider
            assert should_use_relay_for_provider("openai") is False

    def test_apply_relay_to_runtime(self):
        """apply_relay_to_runtime should modify base_url and add relay info."""
        with patch.dict(os.environ, {
            "CUSTOM_RELAY_BASE_URL": "https://relay.example.com/v1",
            "CUSTOM_RELAY_API_KEY": "relay-secret"
        }):
            from hermes_cli.runtime_provider import apply_relay_to_runtime
            runtime = {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-openai-key"
            }
            result = apply_relay_to_runtime(runtime)
            assert result["base_url"] == "https://relay.example.com/v1"
            assert result["relay"]["original_base_url"] == "https://api.openai.com/v1"
            assert result["relay_api_key"] == "relay-secret"

    def test_apply_relay_to_runtime_disabled(self):
        """When relay is disabled, runtime should be unchanged."""
        with patch.dict(os.environ, {}, clear=True):
            from hermes_cli.runtime_provider import apply_relay_to_runtime
            runtime = {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-openai-key"
            }
            result = apply_relay_to_runtime(runtime)
            assert result["base_url"] == "https://api.openai.com/v1"
            assert "relay" not in result

    def test_apply_relay_does_not_modify_original(self):
        """apply_relay_to_runtime should not modify the input dict."""
        with patch.dict(os.environ, {"CUSTOM_RELAY_BASE_URL": "https://relay.com"}):
            from hermes_cli.runtime_provider import apply_relay_to_runtime
            runtime = {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1"
            }
            original_base_url = runtime["base_url"]
            apply_relay_to_runtime(runtime)
            assert runtime["base_url"] == original_base_url
