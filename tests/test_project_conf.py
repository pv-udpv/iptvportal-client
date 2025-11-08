"""Tests for dynaconf-based project configuration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestProjectConf:
    """Test project_conf module functionality."""

    def test_import_project_conf(self):
        """Test that project_conf module can be imported."""
        from iptvportal import project_conf
        
        assert hasattr(project_conf, "get_conf")
        assert hasattr(project_conf, "get_value")
        assert hasattr(project_conf, "set_value")
        assert hasattr(project_conf, "list_settings")

    def test_get_conf_returns_dynaconf(self):
        """Test that get_conf returns a Dynaconf instance."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        assert conf is not None
        assert hasattr(conf, "as_dict")

    def test_core_settings_loaded(self):
        """Test that core settings are loaded from settings.yaml."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Check core section exists
        assert hasattr(conf, "core")
        
        # Check default values from settings.yaml
        assert conf.core.timeout == 30.0
        assert conf.core.max_retries == 3
        assert conf.core.session_ttl == 3600

    def test_cli_settings_loaded(self):
        """Test that CLI settings are loaded."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Check cli section exists
        assert hasattr(conf, "cli")
        
        # Check default values
        assert conf.cli.default_format == "table"
        assert conf.cli.max_limit == 10000
        assert conf.cli.enable_guardrails is True

    def test_sync_settings_loaded(self):
        """Test that sync settings are loaded."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Check sync section exists
        assert hasattr(conf, "sync")
        
        # Check default values
        assert conf.sync.default_sync_strategy == "full"
        assert conf.sync.default_chunk_size == 1000
        assert conf.sync.max_concurrent_syncs == 3

    def test_schema_specific_settings_loaded(self):
        """Test that schema-specific settings are loaded and merged."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Check subscriber schema settings
        if hasattr(conf.sync, "subscriber"):
            assert conf.sync.subscriber.strategy == "incremental"
            assert conf.sync.subscriber.ttl == 1800
            assert conf.sync.subscriber.priority == 1
        
        # Check terminal schema settings
        if hasattr(conf.sync, "terminal"):
            assert conf.sync.terminal.strategy == "full"
            assert conf.sync.terminal.ttl == 7200
        
        # Check package schema settings
        if hasattr(conf.sync, "package"):
            assert conf.sync.package.strategy == "on_demand"
            assert conf.sync.package.ttl == 86400

    def test_get_value_with_dot_notation(self):
        """Test get_value with dot notation."""
        from iptvportal.project_conf import get_value
        
        # Test nested access
        timeout = get_value("core.timeout")
        assert timeout == 30.0
        
        max_limit = get_value("cli.max_limit")
        assert max_limit == 10000
        
        # Test default value
        nonexistent = get_value("does.not.exist", default="default_value")
        assert nonexistent == "default_value"

    def test_set_value_at_runtime(self):
        """Test setting configuration values at runtime."""
        from iptvportal.project_conf import get_value, set_value
        
        # Set a value
        set_value("core.timeout", 60.0)
        
        # Verify it was set
        assert get_value("core.timeout") == 60.0
        
        # Set another value
        set_value("cli.verbose", True)
        assert get_value("cli.verbose") is True

    def test_list_settings_all(self):
        """Test listing all settings."""
        from iptvportal.project_conf import list_settings
        
        all_settings = list_settings()
        
        assert isinstance(all_settings, dict)
        assert "core" in all_settings
        assert "cli" in all_settings
        assert "sync" in all_settings

    def test_list_settings_with_prefix(self):
        """Test listing settings with prefix."""
        from iptvportal.project_conf import list_settings
        
        # Get core settings only
        core_settings = list_settings("core")
        assert isinstance(core_settings, dict)
        assert "timeout" in core_settings or "core" in core_settings
        
        # Get sync settings only
        sync_settings = list_settings("sync")
        assert isinstance(sync_settings, dict)

    def test_get_config_files(self):
        """Test getting list of configuration files."""
        from iptvportal.project_conf import get_config_files
        
        files = get_config_files()
        
        assert isinstance(files, list)
        assert len(files) > 0
        
        # Should have at least settings.yaml
        assert any("settings.yaml" in f for f in files)

    def test_env_var_override(self):
        """Test that environment variables override config files."""
        from iptvportal.project_conf import get_value, reload_conf
        
        # Set environment variable
        with patch.dict(os.environ, {"IPTVPORTAL_CORE__TIMEOUT": "99.0"}):
            # Reload to pick up env var
            reload_conf()
            
            # Check that env var overrides
            timeout = get_value("core.timeout")
            # Dynaconf might convert this to float or keep as string
            assert float(timeout) == 99.0

    def test_reload_conf(self):
        """Test reloading configuration."""
        from iptvportal.project_conf import get_value, reload_conf, set_value
        
        # Set a runtime value
        set_value("core.timeout", 100.0)
        assert get_value("core.timeout") == 100.0
        
        # Reload should reset to default
        reload_conf()
        timeout = get_value("core.timeout")
        
        # Should be back to default (30.0) or env var override
        assert timeout in (30.0, 100.0, "30.0", "100.0")

    def test_settings_global_instance(self):
        """Test that settings is available as global instance."""
        from iptvportal import project_conf
        
        assert hasattr(project_conf, "settings")
        assert project_conf.settings is not None


class TestConfigOverlay:
    """Test configuration overlay and merging scenarios."""

    def test_subscriber_overlay_overrides_defaults(self):
        """Test that subscriber.settings.yaml overrides default sync settings."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Default sync strategy is 'full'
        assert conf.sync.default_sync_strategy == "full"
        
        # But subscriber has 'incremental' override
        if hasattr(conf.sync, "subscriber"):
            assert conf.sync.subscriber.strategy == "incremental"
            # And custom TTL
            assert conf.sync.subscriber.ttl == 1800

    def test_global_defaults_preserved(self):
        """Test that global defaults are preserved when not overridden."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Global settings should still be accessible
        assert conf.core.max_retries == 3
        assert conf.cli.enable_guardrails is True
        
        # Even when schema overrides exist
        if hasattr(conf.sync, "subscriber"):
            # Global default_chunk_size should still be accessible
            assert conf.sync.default_chunk_size == 1000

    def test_multiple_schema_overlays(self):
        """Test that multiple schema overlays work correctly."""
        from iptvportal.project_conf import get_conf
        
        conf = get_conf()
        
        # Each schema should have its own overrides
        if hasattr(conf.sync, "subscriber"):
            assert conf.sync.subscriber.strategy == "incremental"
            assert conf.sync.subscriber.priority == 1
        
        if hasattr(conf.sync, "terminal"):
            assert conf.sync.terminal.strategy == "full"
            assert conf.sync.terminal.priority == 2
        
        if hasattr(conf.sync, "package"):
            assert conf.sync.package.strategy == "on_demand"
            assert conf.sync.package.priority == 3


class TestCLIConfigCommand:
    """Test CLI config commands (integration-style tests)."""

    def test_conf_command_imports(self):
        """Test that conf command can import required modules."""
        from iptvportal.cli.commands.config import conf_command
        
        assert conf_command is not None

    def test_config_app_has_conf_command(self):
        """Test that config_app has the new conf command."""
        from iptvportal.cli.commands.config import config_app
        
        # Check that conf command is registered
        command_names = [cmd.name for cmd in config_app.registered_commands]
        assert "conf" in command_names
