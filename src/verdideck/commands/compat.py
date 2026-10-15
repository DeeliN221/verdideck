"""AiiDA command compatibility helpers for supported verdi versions."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any, cast

_ENTRY_POINT_SCAN_ATTEMPTED = False


def is_aiida_entry_point_cache_error(error: BaseException) -> bool:
    """Check whether AiiDA failed because the reentry entry point cache is stale."""
    error_text = str(error).lower()
    return "not a valid entry point string" in error_text or "reentry scan" in error_text


def refresh_aiida_entry_point_cache() -> None:
    """Refresh AiiDA reentry cache once so users do not need to run repair commands."""
    global _ENTRY_POINT_SCAN_ATTEMPTED

    if _ENTRY_POINT_SCAN_ATTEMPTED:
        return

    _ENTRY_POINT_SCAN_ATTEMPTED = True

    from aiida.plugins import entry_point
    from reentry.default_manager import DEFAULT_MANAGER

    # AiiDA 1.x owns a distinct manager: updating the default manager alone
    # leaves its in-memory entry-point map stale.
    manager = getattr(entry_point, "ENTRYPOINT_MANAGER", DEFAULT_MANAGER)
    scan = getattr(manager, "scan", DEFAULT_MANAGER.scan)
    scan(group_re=r"^aiida\.")
    for name in ("get_entry_points", "get_entry_point", "is_registered_entry_point"):
        clear = getattr(getattr(entry_point, name, None), "cache_clear", None)
        if clear is not None:
            clear()


def get_aiida_version() -> str:
    """Return the installed AiiDA version for user-facing compatibility messages."""
    try:
        from aiida import __version__

        return str(__version__)
    except Exception:
        return "unknown"


def make_environment_error_command(
    command_label: str, import_error: BaseException
) -> Callable[[], str]:
    """Build a visible fallback for AiiDA environment or entry point cache failures."""

    def environment_error_command() -> str:
        """Explain that the AiiDA command failed to load because of the local environment."""
        version = get_aiida_version()
        if isinstance(import_error, ModuleNotFoundError):
            reason = (
                "The verdideck environment is missing runtime dependencies. "
                "Reinstall verdideck."
            )
        elif is_aiida_entry_point_cache_error(import_error):
            reason = (
                "The AiiDA plugin index is still unavailable. "
                "Reinstall verdideck in the active AiiDA environment."
            )
        else:
            reason = f"{type(import_error).__name__}: {import_error}"

        return (
            f"The current environment cannot load `{command_label}` "
            f"for AiiDA {version}.\n\n"
            "This usually indicates an environment mismatch between verdideck and verdi, "
            "or an invalid AiiDA entry point cache. Automatic repair did not resolve the problem.\n"
            f"Reason: {reason}"
        )

    environment_error_command.__name__ = f"environment_error_{command_label.replace(' ', '_')}"
    return environment_error_command


def make_unsupported_command(command_label: str, import_error: BaseException) -> Callable[[], str]:
    """Build a visible fallback command for verdi features missing in the current AiiDA."""

    def unsupported_command() -> str:
        """Explain that this verdi feature is unavailable in the current AiiDA."""
        version = get_aiida_version()
        return (
            f"The `{command_label}` tab is unsupported with the current AiiDA {version}.\n\n"
            "The required verdi command interface is unavailable in this environment.\n"
            f"Import error: {import_error}"
        )

    unsupported_command.__name__ = f"unsupported_{command_label.replace(' ', '_')}"
    return unsupported_command


def import_aiida_command(
    module_name: str,
    attribute_name: str,
    command_label: str,
) -> Callable[..., Any]:
    """Import a verdi command or return a user-visible unsupported fallback."""
    try:
        # Populate legacy plugins before importing cmdline: a failed import can
        # leave partially initialized AiiDA modules in sys.modules.
        if get_aiida_version().startswith("1."):
            refresh_aiida_entry_point_cache()
        module = import_module(module_name)
        return cast(Callable[..., Any], getattr(module, attribute_name))
    except Exception as exc:
        if is_aiida_entry_point_cache_error(exc):
            try:
                refresh_aiida_entry_point_cache()
                module = import_module(module_name)
                return cast(Callable[..., Any], getattr(module, attribute_name))
            except Exception as retry_exc:
                return make_environment_error_command(command_label, retry_exc)
        return make_unsupported_command(command_label, exc)


computer_list = import_aiida_command(
    "aiida.cmdline.commands.cmd_computer", "computer_list", "computer"
)
code_list = import_aiida_command("aiida.cmdline.commands.cmd_code", "code_list", "code")
plugin_list = import_aiida_command("aiida.cmdline.commands.cmd_plugin", "plugin_list", "plugin")
process_list = import_aiida_command(
    "aiida.cmdline.commands.cmd_process", "process_list", "process"
)
verdi_calcjob = import_aiida_command(
    "aiida.cmdline.commands.cmd_calcjob", "verdi_calcjob", "calcjob"
)
group_list = import_aiida_command("aiida.cmdline.commands.cmd_group", "group_list", "group")
node_list = import_aiida_command("aiida.cmdline.commands.cmd_node", "node_list", "node")
verdi_config_list = import_aiida_command(
    "aiida.cmdline.commands.cmd_config", "verdi_config_list", "config"
)
profile_list = import_aiida_command(
    "aiida.cmdline.commands.cmd_profile", "profile_list", "profile"
)
daemon_status = import_aiida_command("aiida.cmdline.commands.cmd_daemon", "status", "daemon")
storage_info = import_aiida_command(
    "aiida.cmdline.commands.cmd_storage", "storage_info", "storage"
)
verdi_presto = import_aiida_command(
    "aiida.cmdline.commands.cmd_presto", "verdi_presto", "presto"
)


COMMAND_PATHS: dict[str, tuple[Callable[..., Any], list[str]]] = {
    "computer": (computer_list, ["computer", "list", "-r", "-a"]),
    "code": (code_list, ["code", "list"]),
    "plugin": (plugin_list, ["plugin", "list"]),
    "process": (process_list, ["process", "list"]),
    "calcjob": (verdi_calcjob, ["calcjob"]),
    "config": (verdi_config_list, ["config", "list"]),
    "profile": (profile_list, ["profile", "list"]),
    "group": (group_list, ["group", "list"]),
    "node": (node_list, ["node", "list"]),
    "presto": (verdi_presto, ["presto"]),
    "daemon": (daemon_status, ["daemon", "status"]),
    "storage": (storage_info, ["storage", "info"]),
}

VERDI_COMMAND_PATHS: dict[int, list[str]] = {
    id(command): path for command, path in COMMAND_PATHS.values()
}


def get_command_path(command_func: Callable[..., Any]) -> list[str] | None:
    """Return the verdi command path for a registered command object."""
    return VERDI_COMMAND_PATHS.get(id(command_func))
