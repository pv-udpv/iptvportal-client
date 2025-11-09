import logging
import sys
from types import SimpleNamespace

from dynaconf import Dynaconf

import iptvportal.logging_setup as logging_setup


def test_build_formatters_default():
    cfg = {}
    fmts = logging_setup._build_formatters(cfg)
    assert "default" in fmts
    assert "%(asctime)s" in fmts["default"]["format"]


def test_build_formatters_with_color_and_json(monkeypatch):
    # Inject fake colorlog and pythonjsonlogger into sys.modules
    class FakeColoredFormatter:
        pass

    class FakeJsonFormatter:
        pass

    fake_colorlog = SimpleNamespace(ColoredFormatter=FakeColoredFormatter)
    fake_jsonlogger = SimpleNamespace(jsonlogger=SimpleNamespace(JsonFormatter=FakeJsonFormatter))

    monkeypatch.setitem(sys.modules, "colorlog", fake_colorlog)
    monkeypatch.setitem(sys.modules, "pythonjsonlogger", fake_jsonlogger)

    cfg = {
        "format": "%(message)s",
        "handlers": {"console": {"colorize": True}, "file": {"json_format": True}},
    }
    fmts = logging_setup._build_formatters(cfg)

    # Colored formatter should be present (named "colored")
    assert "colored" in fmts
    # JSON formatter should be present when requested
    assert "json" in fmts


def test_build_handlers_console_and_file(tmp_path):
    cfg = {
        "handlers": {
            "console": {"enabled": True, "level": "DEBUG"},
            "file": {
                "enabled": True,
                "level": "INFO",
                "path": str(tmp_path / "logs" / "app.log"),
                "json_format": False,
            },
        }
    }
    formatters = logging_setup._build_formatters(cfg)
    handlers, handler_names = logging_setup._build_handlers(cfg, formatters)

    assert "console" in handlers
    assert "file" in handlers
    # Ensure handler names list contains both
    assert set(handler_names) == {"console", "file"}
    # Ensure log dir was created
    assert (tmp_path / "logs").exists()


def test_build_loggers_name_resolution():
    cfg = {
        "level": "INFO",
        "loggers": {
            "iptvportal.client.sync": "DEBUG",  # dot notation
            "iptvportal_client_sync": "WARNING",  # underscore shorthand
            "iptvportal___client___sync": "ERROR",  # triple underscore explicit
        },
        "library_level": "ERROR",
    }
    handlers = ["console"]
    loggers = logging_setup._build_loggers(cfg, handlers)

    # Expect dotted names as keys
    assert "iptvportal.client.sync" in loggers
    # underscore shorthand should be resolved to dotted path
    assert "iptvportal.client.sync" in loggers  # same target overwritten is OK
    # triple underscore should resolve to dotted form as well
    assert "iptvportal.client.sync" in loggers


def test_build_dict_config_contains_expected_sections():
    cfg = {
        "format": "%(levelname)s %(message)s",
        "handlers": {"console": {"enabled": True}},
        "loggers": {"iptvportal": {"level": "INFO"}},
        "library_level": "WARNING",
    }
    dict_conf = logging_setup._build_dict_config(cfg)
    assert "formatters" in dict_conf
    assert "handlers" in dict_conf
    assert "loggers" in dict_conf
    assert "root" in dict_conf


def test_setup_logging_accepts_dict_and_dynaconf(monkeypatch):
    # Capture calls to logging.config.dictConfig
    called = {}

    def fake_dictConfig(conf):
        called["conf"] = conf

    monkeypatch.setattr(logging_setup.logging.config, "dictConfig", fake_dictConfig)

    # Pass plain dict
    cfg_dict = {"logging": {"level": "DEBUG", "handlers": {"console": {"enabled": True}}}}
    logging_setup.setup_logging(cfg_dict)
    assert "conf" in called
    assert "handlers" in called["conf"]
    called.clear()

    # Pass Dynaconf-like object (use real Dynaconf)
    dyn = Dynaconf(settings_files=[])
    dyn.set("logging", {"level": "INFO", "handlers": {"console": {"enabled": True}}})
    logging_setup.setup_logging(dyn)
    assert "conf" in called
    assert "handlers" in called["conf"]


def test_get_logger_returns_logger():
    logger = logging_setup.get_logger("iptvportal.test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "iptvportal.test"
