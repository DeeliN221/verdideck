"""Batch data loader for efficient startup loading.

This module provides a mechanism to load all panel data in a single database session,
avoiding SQLAlchemy session conflicts while minimizing startup time.
"""

from typing import Any

from verdideck.commands.base import STARTUP_COMMANDS
from verdideck.core.click_compat import create_cli_runner


def _run_command_in_batch(command_func: Any, args: list[str]) -> tuple[str, str, int]:
    """Run a single command and return its output.

    Args:
        command_func: Command function to execute
        args: Command arguments

    Returns:
        Tuple of (stdout, stderr, exit_code)
    """
    # Handle non-Click commands (pure Python functions)
    if callable(command_func) and not hasattr(command_func, "callback"):
        try:
            output = command_func()
            return str(output) if output else "", "", 0
        except Exception as e:
            return "", str(e), 1

    # Handle Click commands
    cli_runner = create_cli_runner()

    # Check if this is a VerdiCommand that needs main verdi context
    is_verdi_command = (
        hasattr(command_func, "__class__") and command_func.__class__.__name__ == "VerdiCommand"
    )

    try:
        if is_verdi_command:
            from aiida.cmdline.commands.cmd_verdi import verdi

            from verdideck.commands.compat import VERDI_COMMAND_PATHS

            # Look up the command path in our mapping
            cmd_path = VERDI_COMMAND_PATHS.get(id(command_func), [])

            if cmd_path:
                verdi_args = cmd_path + args
            else:
                # Fallback: use command's name attribute
                cmd_name = getattr(command_func, "name", "")
                verdi_args = [cmd_name] + args

            cli_result = cli_runner.invoke(verdi, verdi_args, catch_exceptions=True)
        else:
            # For non-VerdiCommand Click commands, invoke directly
            cli_result = cli_runner.invoke(command_func, args, catch_exceptions=True)  # type: ignore[arg-type]

        stdout = cli_result.stdout
        stderr = cli_result.stderr_bytes.decode() if cli_result.stderr_bytes else ""
        exit_code = cli_result.exit_code or 0

        return stdout, stderr, exit_code
    except Exception as e:
        return "", str(e), 1


def load_all_startup_data() -> dict[str, dict[str, Any]]:
    """Load data for all panels in a single batch operation.

    This function executes all startup commands sequentially in the same thread/session,
    avoiding SQLAlchemy session conflicts while being faster than running commands
    separately in isolated sessions.

    Returns:
        Dictionary mapping panel_id -> tab_name -> command_result
        Example:
        {
            "panel-1": {
                "computer": {"stdout": "...", "stderr": "...", "exit_code": 0}
            },
            ...
        }
    """
    results: dict[str, dict[str, Any]] = {}

    # Define commands for each panel's default tab
    # Only load the first (default) tab for each panel at startup
    commands_to_run: list[tuple[str, str, Any, list[str]]] = [
        (panel_id, _get_startup_tab_name(panel_id), command_func, args)
        for panel_id, (command_func, args) in STARTUP_COMMANDS.items()
    ]

    # Execute all commands sequentially in the same session
    for panel_id, tab_name, cmd_func, args in commands_to_run:
        try:
            stdout, stderr, exit_code = _run_command_in_batch(cmd_func, args)

            if panel_id not in results:
                results[panel_id] = {}

            results[panel_id][tab_name] = {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as e:
            if panel_id not in results:
                results[panel_id] = {}

            results[panel_id][tab_name] = {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
            }

    return results


def _get_startup_tab_name(panel_id: str) -> str:
    """Return the default tab name used for a panel during startup loading."""
    return {
        "panel-1": "computer",
        "panel-2": "process",
        "panel-3": "group",
        "panel-4": "config",
        "panel-5": "status",
    }.get(panel_id, panel_id)


def load_tab_data(
    panel_id: str, tab_name: str, command_func: Any, args: list[str]
) -> dict[str, Any]:
    """Load data for a specific tab when user switches to it.

    Args:
        panel_id: Panel identifier (e.g., "panel-1")
        tab_name: Tab name (e.g., "code", "plugin")
        command_func: Command function to execute
        args: Command arguments

    Returns:
        Command result dictionary with stdout, stderr, exit_code
    """
    try:
        stdout, stderr, exit_code = _run_command_in_batch(command_func, args)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1,
        }
