"""AiiDA 1.6.9 compatibility contract: imports, fallbacks, status and Click execution."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Sequence
from typing import Any

import pytest
from aiida import __version__ as aiida_version

pytestmark = pytest.mark.skipif(aiida_version != "1.6.9", reason="Requires AiiDA 1.6.9")


def _assert_aiida_169() -> None:
    """Require the dedicated AiiDA 1.6.9 test environment."""
    aiida = importlib.import_module("aiida")
    assert aiida.__version__ == "1.6.9", (
        "Run this contract with AiiDA 1.6.9; "
        f"detected {aiida.__version__!r}"
    )


def _find_tab(tabs: Sequence[tuple[Any, ...]], tab_name: str) -> tuple[Any, ...]:
    """Find a named tab in the panel configuration."""
    for tab in tabs:
        if tab and tab[0] == tab_name:
            return tab
    raise AssertionError(f"Missing required tab: {tab_name}")


def test_verdideck_imports_in_aiida_169() -> None:
    """Import verdideck and expose command registries with legacy AiiDA."""
    _assert_aiida_169()

    verdideck = importlib.import_module("verdideck")
    commands = importlib.import_module("verdideck.commands")

    assert hasattr(verdideck, "CommandRunner")
    assert hasattr(commands, "TABLE_TABS")
    assert hasattr(commands, "PANEL_TABS")


def test_unsupported_tabs_are_visible_and_explain_aiida_version() -> None:
    """Keep unsupported node and storage tabs visible with an explanation."""
    _assert_aiida_169()

    commands = importlib.import_module("verdideck.commands")
    runner_module = importlib.import_module("verdideck.core.runner")

    node_tab = _find_tab(commands.TABLE_TABS["panel-3"], "node")
    storage_tab = _find_tab(commands.PANEL_TABS["panel-5"], "storage")

    async def run_tab(tab: tuple[Any, ...]) -> str:
        """Run the tab command and return its visible output."""
        command_func = tab[1]
        args = tab[2]
        result = await runner_module.CommandRunner().run_command(command_func, args)
        assert result.exit_code == 0
        return "\n".join(part for part in [result.stdout, result.stderr] if part)

    node_output = asyncio.run(run_tab(node_tab))
    storage_output = asyncio.run(run_tab(storage_tab))

    for output in [node_output, storage_output]:
        assert "1.6.9" in output
        assert "unsupported" in output.lower()


def test_status_formats_configuration_version_error(monkeypatch: Any) -> None:
    """Explain configuration version errors without a traceback."""
    _assert_aiida_169()

    base = importlib.import_module("verdideck.commands.base")
    configuration = importlib.import_module("aiida.manage.configuration")

    def raise_configuration_version_error() -> None:
        """Simulate AiiDA 1.6.9 reading an incompatible configuration."""
        raise RuntimeError(
            "The configuration file has version 9 which is not compatible "
            "with the current version 5."
        )

    monkeypatch.setattr(configuration, "get_config", raise_configuration_version_error)

    output = base.get_aiida_status()
    lower_output = output.lower()

    assert "AiiDA v1.6.9" in output
    assert "traceback" not in lower_output
    assert "not compatible" in lower_output or "configuration version" in lower_output
    assert "quicksetup" not in lower_output


def test_runner_executes_aiida_169_click_command() -> None:
    """Execute an ordinary Click command from AiiDA 1.6.9."""
    _assert_aiida_169()

    from aiida.cmdline.commands.cmd_computer import computer_list

    from verdideck.core import CommandRunner

    result = asyncio.run(CommandRunner().run_command(computer_list, ["--help"]))

    assert result.exit_code == 0
    assert "List all available computers" in result.stdout


def test_first_launch_with_empty_plugin_cache(tmp_path: Any) -> None:
    """A fresh install must load real commands without a previous reentry scan."""
    import os
    import subprocess
    import sys

    environment = dict(os.environ, REENTRY_DATADIR=str(tmp_path / "plugins"))
    result = subprocess.run(
        [sys.executable, "-c",
         "import verdideck; "
         "from verdideck.commands.compat import computer_list; "
         "from aiida.cmdline.commands.cmd_computer import computer_list as expected; "
         "assert computer_list is expected"],
        env=environment, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
