"""Tests for AiiDA command compatibility fallbacks."""

from types import SimpleNamespace
from typing import Any

import verdideck.commands.compat as compat
from verdideck.commands.compat import (
    import_aiida_command,
    is_aiida_entry_point_cache_error,
    make_environment_error_command,
)


def test_detect_reentry_cache_error() -> None:
    """Test that reentry cache failures are treated as environment errors."""
    error = ValueError(
        "aiida.groups:core is not a valid entry point string: "
        "Try running `reentry scan` to update the entry point cache."
    )

    assert is_aiida_entry_point_cache_error(error)


def test_environment_error_message_does_not_claim_unsupported() -> None:
    """Test that entry point cache failures do not claim AiiDA lacks a command."""
    command = make_environment_error_command("process", RuntimeError("run reentry scan"))

    message = command()

    assert "environment mismatch" in message
    assert "Automatic repair" in message
    assert "unsupported with" not in message


def test_environment_error_message_hides_internal_dependency_name() -> None:
    """Test that missing repair dependencies are explained without Python internals."""
    command = make_environment_error_command("process", ModuleNotFoundError("pkg_resources"))

    message = command()

    assert "missing runtime dependencies" in message
    assert "pkg_resources" not in message


def test_import_command_refreshes_entry_points_and_retries(monkeypatch: Any) -> None:
    """Test that a stale entry point cache is repaired silently before falling back."""
    calls = {"import": 0, "scan": 0}
    command = object()

    def fake_import_module(module_name: str) -> Any:
        """Raise a cache error once, then return a module with the requested command."""
        calls["import"] += 1
        if calls["import"] == 1:
            raise ValueError("aiida.groups:core is not a valid entry point string")
        return SimpleNamespace(process_list=command)

    monkeypatch.setattr(compat, "_ENTRY_POINT_SCAN_ATTEMPTED", False)
    monkeypatch.setattr(compat, "import_module", fake_import_module)
    monkeypatch.setattr(
        compat,
        "refresh_aiida_entry_point_cache",
        lambda: calls.__setitem__("scan", calls["scan"] + 1),
    )

    result = import_aiida_command("aiida.cmdline.commands.cmd_process", "process_list", "process")

    assert result is command
    assert calls == {"import": 2, "scan": 1}
