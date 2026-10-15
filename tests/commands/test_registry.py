"""Tests for command registry."""

from verdideck.commands import STARTUP_COMMANDS, format_error_message


def test_startup_commands_defined() -> None:
    """Test that all startup commands are defined."""
    assert len(STARTUP_COMMANDS) == 5
    assert "panel-1" in STARTUP_COMMANDS
    assert "panel-5" in STARTUP_COMMANDS


def test_startup_commands_structure() -> None:
    """Test startup commands have correct structure."""
    for panel_id, (cmd_func, args) in STARTUP_COMMANDS.items():
        assert callable(cmd_func)
        assert isinstance(args, list)


def test_format_error_profile() -> None:
    """Test error formatting for profile errors."""
    msg = format_error_message("profile_list", "No profile configured")
    assert "quicksetup" in msg.lower()
    assert "setup" in msg.lower()


def test_format_error_computer() -> None:
    """Test error formatting for computer errors."""
    msg = format_error_message("computer_list", "No computers")
    assert "computer setup" in msg.lower()


def test_format_error_process() -> None:
    """Test error formatting for process errors."""
    msg = format_error_message("process_list", "No processes")
    assert "submit" in msg.lower() or "calculation" in msg.lower()


def test_format_error_generic() -> None:
    """Test generic error formatting."""
    msg = format_error_message("some_command", "Generic error")
    assert "Generic error" in msg
