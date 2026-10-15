"""Command execution engine for running verdi commands asynchronously."""

import asyncio
import inspect
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional

from verdideck.core.click_compat import create_cli_runner


def _is_verdi_command(command_func: Callable[..., object]) -> bool:
    """Check if a command is a VerdiCommand that needs the main verdi context.

    Args:
        command_func: Command function to check

    Returns:
        True if this is a VerdiCommand
    """
    return hasattr(command_func, "__class__") and command_func.__class__.__name__ == "VerdiCommand"


def _cleanup_aiida_session() -> None:
    """Clean up AiiDA database session in the current thread.

    This must be called from within the worker thread to properly clean up
    thread-local scoped sessions and cached objects.
    """
    try:
        from aiida.manage.manager import get_manager
        from aiida.orm.entities import Collection

        manager = get_manager()
        if manager.profile_storage_loaded:
            backend = manager.get_profile_storage()

            # Remove scoped session - this clears the thread-local session
            if hasattr(backend, "_session_factory"):
                session_factory = backend._session_factory  # type: ignore[attr-defined]
                if hasattr(session_factory, "remove"):
                    session_factory.remove()

            # Also expire all objects in the session to prevent DetachedInstanceError
            if hasattr(backend, "get_session"):
                try:
                    session = backend.get_session()  # type: ignore[attr-defined]
                    if session and hasattr(session, "expire_all"):
                        session.expire_all()
                except Exception:
                    pass

            # Clear the cached default user to prevent DetachedInstanceError
            if hasattr(backend, "_default_user"):
                backend._default_user = None  # type: ignore[attr-defined]

            # Clear the Collection LRU cache to prevent stale object references
            if hasattr(Collection, "get_cached"):
                cache_info = getattr(Collection.get_cached, "cache_info", None)
                if cache_info is not None:  # Has LRU cache
                    Collection.get_cached.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


def _run_click_command_isolated(
    command_func: Callable[..., Any],
    args: list[str],
    is_verdi_command: bool,
) -> tuple[str, str, int, Optional[BaseException]]:
    """Run a Click command in isolation with proper session cleanup.

    This function is designed to be run in a separate thread via asyncio.to_thread.
    It handles session cleanup before and after command execution within the same thread.

    Args:
        command_func: Click command function to execute
        args: Command line arguments
        is_verdi_command: Whether this is a VerdiCommand needing main verdi context

    Returns:
        Tuple of (stdout, stderr, exit_code, exception)
    """
    # Clean up any lingering session from previous commands in this thread
    _cleanup_aiida_session()

    try:
        cli_runner = create_cli_runner()

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
            cli_result = cli_runner.invoke(command_func, args, catch_exceptions=True)  # type: ignore[arg-type]

        stdout = cli_result.stdout
        stderr = cli_result.stderr_bytes.decode() if cli_result.stderr_bytes else ""
        exit_code = cli_result.exit_code or 0
        exception = cli_result.exception

        return stdout, stderr, exit_code, exception

    finally:
        # Clean up session after command execution
        _cleanup_aiida_session()


@dataclass
class CommandResult:
    """Result of a command execution."""

    cmd: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    status: Literal["running", "done", "cancelled", "failed"] = "running"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> float:
        """Calculate command execution duration in seconds."""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success(self) -> bool:
        """Check if command completed successfully."""
        return self.exit_code == 0 and self.status == "done"


class CommandRunner:
    """Async command runner for verdi commands with priority queue support.

    Commands are executed serially to avoid SQLAlchemy session conflicts,
    but high-priority commands (from focused panels) skip to the front of the queue.
    """

    # Class-level lock and queue shared across all instances
    _lock: Optional[asyncio.Lock] = None
    _priority_event: Optional[asyncio.Event] = None
    _current_priority: int = 0  # 0 = normal, 1 = high priority

    def __init__(self) -> None:
        """Initialize command runner."""
        pass

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Get or create the global lock."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    async def run_command(
        self,
        command_func: Callable[..., object],
        args: Optional[list[str]] = None,
        callback: Optional[Callable[[CommandResult], None]] = None,
        priority: bool = False,
    ) -> CommandResult:
        """Run a verdi command asynchronously.

        Args:
            command_func: Click command function or regular Python function to execute
            args: Command line arguments (ignored for regular Python functions)
            callback: Optional callback function called on completion
            priority: If True, this command has high priority (e.g., from focused panel)

        Returns:
            CommandResult with execution details

        Note:
            Commands are serialized to prevent SQLAlchemy session conflicts.
            High-priority commands will execute before normal-priority commands
            that are waiting for the lock.
        """
        cmd_name = getattr(
            command_func, "name", getattr(command_func, "__name__", str(command_func))
        )
        result = CommandResult(cmd=f"verdi {cmd_name} {' '.join(args or [])}")

        lock = self._get_lock()

        # Acquire lock - commands execute serially
        async with lock:
            try:
                # Check if this is a regular Python function (not a Click command)
                if inspect.isfunction(command_func) and not hasattr(command_func, "callback"):
                    # Direct Python function call - wrap with session cleanup
                    def run_with_cleanup() -> Any:
                        _cleanup_aiida_session()
                        try:
                            return command_func()
                        finally:
                            _cleanup_aiida_session()

                    try:
                        output = await asyncio.to_thread(run_with_cleanup)
                        result.stdout = str(output) if output else ""
                        result.exit_code = 0
                        result.status = "done"
                    except asyncio.CancelledError:
                        result.status = "cancelled"
                        raise
                else:
                    # Run Click command in isolated thread with session cleanup
                    is_verdi = _is_verdi_command(command_func)

                    stdout, stderr, exit_code, exception = await asyncio.to_thread(
                        _run_click_command_isolated,
                        command_func,
                        args or [],
                        is_verdi,
                    )

                    result.stdout = stdout
                    result.stderr = stderr
                    result.exit_code = exit_code
                    result.status = "done" if exit_code == 0 else "failed"

                    # If command failed with exception, include full traceback in stderr
                    if exception:
                        exc_type = type(exception).__name__
                        exc_msg = str(exception)
                        exc_tb = "".join(
                            traceback.format_exception(
                                type(exception),
                                exception,
                                exception.__traceback__,
                            )
                        )

                        if not result.stderr:
                            result.stderr = f"{exc_type}: {exc_msg}\n\n{exc_tb}"
                        else:
                            result.stderr += f"\n\n{exc_type}: {exc_msg}\n\n{exc_tb}"

            except asyncio.CancelledError:
                result.status = "cancelled"
                raise
            except Exception as e:
                result.status = "failed"
                result.stderr = str(e)
                result.exit_code = 1
            finally:
                result.end_time = datetime.now()
                if callback:
                    callback(result)

        return result
