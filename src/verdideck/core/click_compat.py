"""Create Click runners with separate output streams across Click versions."""

from inspect import signature
from typing import Any

from click.testing import CliRunner


def create_cli_runner() -> CliRunner:
    """Click 8.2 removed mix_stderr and always captures stderr separately."""
    options: dict[str, Any] = {}
    if "mix_stderr" in signature(CliRunner).parameters:
        options["mix_stderr"] = False
    return CliRunner(**options)
