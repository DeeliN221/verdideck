"""Tests for CommandRunner."""

import asyncio

import click
import pytest

from verdideck.core import CommandResult, CommandRunner


@click.command()
def mock_success_cmd() -> None:
    """Mock successful command."""
    click.echo("Success output")


@click.command()
def mock_fail_cmd() -> None:
    """Mock failing command."""
    raise click.ClickException("Command failed")


@click.command()
@click.argument("name")
def mock_arg_cmd(name: str) -> None:
    """Mock command with arguments."""
    click.echo(f"Hello {name}")


@pytest.mark.asyncio
async def test_command_result_duration() -> None:
    """Test CommandResult duration calculation."""
    result = CommandResult(cmd="test")
    await asyncio.sleep(0.1)
    assert result.duration >= 0.1


@pytest.mark.asyncio
async def test_command_result_success() -> None:
    """Test CommandResult success property."""
    result = CommandResult(cmd="test", exit_code=0, status="done")
    assert result.success is True

    result_failed = CommandResult(cmd="test", exit_code=1, status="failed")
    assert result_failed.success is False


@pytest.mark.asyncio
async def test_runner_simple_command() -> None:
    """Test running a simple successful command."""
    runner = CommandRunner()
    result = await runner.run_command(mock_success_cmd)

    assert result.exit_code == 0
    assert result.status == "done"
    assert "Success output" in result.stdout
    assert result.success is True


@pytest.mark.asyncio
async def test_runner_failed_command() -> None:
    """Test running a failing command."""
    runner = CommandRunner()
    result = await runner.run_command(mock_fail_cmd)

    assert result.exit_code != 0
    assert result.status == "failed"
    assert not result.success


@pytest.mark.asyncio
async def test_runner_with_args() -> None:
    """Test running command with arguments."""
    runner = CommandRunner()
    result = await runner.run_command(mock_arg_cmd, args=["World"])

    assert result.exit_code == 0
    assert "Hello World" in result.stdout


@pytest.mark.asyncio
async def test_runner_callback() -> None:
    """Test callback is invoked on completion."""
    runner = CommandRunner()
    callback_result = None

    def callback(result: CommandResult) -> None:
        nonlocal callback_result
        callback_result = result

    result = await runner.run_command(mock_success_cmd, callback=callback)

    assert callback_result is not None
    assert callback_result.cmd == result.cmd


@pytest.mark.asyncio
async def test_runner_cancel() -> None:
    """Test command cancellation.

    Note: This tests cancellation before the command starts executing.
    Commands that are already executing synchronously cannot be interrupted.
    """
    runner = CommandRunner()

    # Create a mock command that will take time
    @click.command()
    def slow_cmd() -> None:
        """Slow command for cancellation test."""
        import time

        time.sleep(2)

    # Create the task
    task = asyncio.create_task(runner.run_command(slow_cmd))

    # Cancel immediately before it gets a chance to start
    task.cancel()

    # The task should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_click_stdout_and_stderr_stay_separate() -> None:
    import click

    from verdideck.core.batch_loader import _run_command_in_batch

    @click.command()
    def streams() -> None:
        click.echo("result")
        click.echo("diagnostic", err=True)

    result = await CommandRunner().run_command(streams)
    assert result.exit_code == 0
    assert result.stdout == "result\n"
    assert result.stderr == "diagnostic\n"
    stdout, stderr, code = _run_command_in_batch(streams, [])
    assert (stdout, stderr, code) == ("result\n", "diagnostic\n", 0)
