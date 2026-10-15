"""Tests for AiiDA status compatibility helpers."""

from types import SimpleNamespace
from typing import Any

from verdideck.commands import base


def test_load_profile_falls_back_to_configuration_api(monkeypatch: Any) -> None:
    """Test that AiiDA 1.x profile loading uses the configuration API fallback."""
    calls: list[str] = []
    manager = SimpleNamespace()

    monkeypatch.setattr(
        "aiida.manage.manager.get_manager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "aiida.manage.configuration.load_profile",
        lambda profile_name: calls.append(profile_name),
    )

    result = base._load_profile_for_current_aiida("test")

    assert result is manager
    assert calls == ["test"]


def test_format_profile_storage_uses_aiida_1_backend() -> None:
    """Test that AiiDA 1.x storage status uses the manager backend fallback."""
    profile = SimpleNamespace(database_backend="django")
    manager = SimpleNamespace(get_backend=lambda: object())

    assert base._format_profile_storage(profile, manager).startswith("django (")


def test_format_profile_broker_uses_aiida_1_profile_config() -> None:
    """Test that AiiDA 1.x broker status uses profile broker settings."""
    profile = SimpleNamespace(
        broker_protocol="amqp",
        broker_username="guest",
        broker_host="127.0.0.1",
        broker_port=5672,
    )
    manager = SimpleNamespace()

    assert base._format_profile_broker(profile, manager) == "amqp://guest@127.0.0.1:5672"
