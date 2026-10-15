"""Command registry and status helpers for verdideck panels."""

from collections.abc import Callable
from typing import Any, Optional

from .compat import (
    code_list,
    computer_list,
    daemon_status,
    get_aiida_version,
    group_list,
    node_list,
    plugin_list,
    process_list,
    profile_list,
    storage_info,
    verdi_calcjob,
    verdi_config_list,
)
from .formatters import (
    format_config_list,
    format_daemon_status,
    format_process_list,
    format_profile_list,
    format_storage_info,
    format_table_output,
    no_format,
)
from .parsers import (
    parse_calcjob_help,
    parse_code_list,
    parse_computer_list,
    parse_group_list,
    parse_node_list,
    parse_plugin_list,
    parse_process_list,
)


def _get_config_dir() -> str:
    """Return the AiiDA configuration directory across AiiDA 1.x and 2.x."""
    try:
        from aiida.manage.configuration.settings import AiiDAConfigDir

        return str(AiiDAConfigDir.get())
    except Exception:
        pass

    try:
        from aiida.manage.configuration import settings

        config_folder = getattr(settings, "AIIDA_CONFIG_FOLDER", None)
        if config_folder:
            return str(config_folder)
    except Exception:
        pass

    try:
        from aiida.manage.configuration import settings

        get_config_path = getattr(settings, "get_config_path")
        return str(get_config_path())
    except Exception as exc:
        return f"Unavailable - {exc}"


def _is_configuration_version_error(error: BaseException) -> bool:
    """Check whether an AiiDA config error is caused by version incompatibility."""
    error_text = str(error).lower()
    return "version" in error_text and "not compatible" in error_text


def _load_profile_for_current_aiida(profile_name: str) -> Any:
    """Load the configured AiiDA profile using the API available in this AiiDA version."""
    from aiida.manage.manager import get_manager

    manager = get_manager()
    manager_load_profile = getattr(manager, "load_profile", None)
    if callable(manager_load_profile):
        manager_load_profile(profile_name)
    else:
        from aiida.manage.configuration import load_profile

        load_profile(profile_name)

    return get_manager()


def _format_profile_storage(profile: Any, manager: Any) -> str:
    """Return a concise storage/backend description across AiiDA 1.x and 2.x."""
    storage_cls = getattr(profile, "storage_cls", None)
    if storage_cls is not None:
        storage_backend = storage_cls(profile)
        return str(storage_backend)

    get_backend = getattr(manager, "get_backend", None)
    if callable(get_backend):
        backend = get_backend()
        backend_name = getattr(profile, "database_backend", type(backend).__name__)
        return f"{backend_name} ({type(backend).__name__})"

    raise AttributeError("No supported AiiDA storage/backend API found")


def _format_profile_broker(profile: Any, manager: Any) -> str:
    """Return broker status using the best API available for the AiiDA version."""
    get_broker = getattr(manager, "get_broker", None)
    if callable(get_broker):
        broker = get_broker()
        if broker:
            broker.get_communicator()
            return str(broker)
        return "No broker"

    broker_host = getattr(profile, "broker_host", None)
    broker_port = getattr(profile, "broker_port", None)
    if broker_host and broker_port:
        broker_protocol = getattr(profile, "broker_protocol", "amqp")
        broker_username = getattr(profile, "broker_username", "guest")
        return f"{broker_protocol}://{broker_username}@{broker_host}:{broker_port}"

    return "No broker"


def get_aiida_status() -> str:
    """Get AiiDA status information directly from internal APIs.

    This function replicates the behavior of 'verdi status' without using subprocess.

    Returns:
        Formatted status string
    """
    output_lines = []

    # Version
    output_lines.append(f"✔ version:     AiiDA v{get_aiida_version()}")

    # Config directory
    config_dir = _get_config_dir()
    output_lines.append(f"✔ config:      {config_dir}")

    # Get config and profile - gracefully handle missing config
    try:
        from aiida.manage.configuration import get_config

        config = get_config()
        profile_name = config.default_profile_name
    except Exception as exc:
        if _is_configuration_version_error(exc):
            output_lines.append(f"✘ profile:     Incompatible configuration version - {exc}")
            output_lines.append(
                "Use a configuration compatible with this AiiDA version, "
                "or switch to a matching AiiDA environment."
            )
            return "\n".join(output_lines)

        # Config file doesn't exist - this is expected for first-time users
        output_lines.append("⚠ profile:     No profile configured")
        output_lines.append("")
        output_lines.append("To set up AiiDA, run:")
        output_lines.append("  verdi quicksetup")
        return "\n".join(output_lines)

    if not profile_name:
        output_lines.append("⚠ profile:     No profile configured")
        output_lines.append("")
        output_lines.append("To set up AiiDA, run:")
        output_lines.append("  verdi quicksetup")
        return "\n".join(output_lines)

    profile = config.get_profile(profile_name)
    output_lines.append(f"✔ profile:     {profile.name}")

    # Load profile
    try:
        manager = _load_profile_for_current_aiida(profile.name)
    except Exception as e:
        output_lines.append(f"✘ error:       Failed to load profile - {e}")
        return "\n".join(output_lines)

    # Storage
    try:
        storage_str = _format_profile_storage(profile, manager)
        # Truncate if too long
        if len(storage_str) > 60:
            storage_str = storage_str[:57] + "..."
        output_lines.append(f"✔ storage:     {storage_str}")
    except Exception as e:
        output_lines.append(f"✘ storage:     {type(e).__name__}")

    # Broker
    try:
        broker_str = _format_profile_broker(profile, manager)
        if broker_str == "No broker":
            output_lines.append("⚠ broker:      No broker")
        else:
            if len(broker_str) > 60:
                broker_str = broker_str[:57] + "..."
            output_lines.append(f"✔ broker:      {broker_str}")
    except Exception:
        output_lines.append("✘ broker:      Unable to connect")

    # Daemon
    try:
        daemon_client = manager.get_daemon_client()
        daemon_status = daemon_client.get_status()
        if daemon_status:
            pid = daemon_status.get("pid", "unknown")
            output_lines.append(f"✔ daemon:      Running (PID {pid})")
        else:
            output_lines.append("✘ daemon:      Not running")
    except Exception:
        output_lines.append("✘ daemon:      Error")

    return "\n".join(output_lines)


# Panel configurations with tabs for TextArea-based panels
# Format: panel_id -> list of (tab_name, command_func, args, formatter)
PANEL_TABS: dict[
    str, list[tuple[str, Callable[..., Any], list[str], Optional[Callable[[str], str]]]]
] = {
    "panel-4": [
        ("config", verdi_config_list, ["--"], format_config_list),
        ("profile", profile_list, [], format_profile_list),
    ],
    "panel-5": [
        ("status", get_aiida_status, [], no_format),
        ("daemon", daemon_status, [], format_daemon_status),
        ("storage", storage_info, [], format_storage_info),
    ],
}

# Table panel configurations for DataTable-based panels
# Format: panel_id -> list of (tab_name, command_func, args, formatter, parser)
TABLE_TABS: dict[
    str,
    list[
        tuple[
            str,
            Callable[..., Any],
            list[str],
            Optional[Callable[[str], str]],
            Callable[[str], dict[str, Any]],
        ]
    ],
] = {
    "panel-1": [
        ("computer", computer_list, [], format_table_output, parse_computer_list),
        ("code", code_list, [], format_table_output, parse_code_list),
        ("plugin", plugin_list, [], format_table_output, parse_plugin_list),
    ],
    "panel-2": [
        ("process", process_list, [], format_process_list, parse_process_list),
        ("calcjob", verdi_calcjob, ["--help"], no_format, parse_calcjob_help),
    ],
    "panel-3": [
        ("group", group_list, [], format_table_output, parse_group_list),
        ("node", node_list, [], format_table_output, parse_node_list),
    ],
}

# Legacy: Status panel uses separate command (deprecated, use PANEL_TABS instead)
STATUS_COMMAND: tuple[Callable[..., Any], list[str]] = (get_aiida_status, [])

# Legacy compatibility - keep for now but deprecated
STARTUP_COMMANDS: dict[str, tuple[Callable[..., Any], list[str]]] = {
    "panel-1": (computer_list, []),
    "panel-2": (process_list, []),
    "panel-3": (group_list, []),
    "panel-4": (profile_list, []),
    "panel-5": (get_aiida_status, []),
}


def format_error_message(cmd_name: str, error: str) -> str:
    """Format friendly error message for failed commands.

    Args:
        cmd_name: Command name
        error: Error message

    Returns:
        Formatted user-friendly message
    """
    if "profile" in cmd_name.lower() or "profile" in error.lower():
        return (
            "No AiiDA profile configured.\n\n"
            "Please run:\n"
            "  verdi quicksetup  (for quick setup)\n"
            "  verdi setup       (for detailed setup)"
        )

    if "computer" in cmd_name.lower() and "No" in error:
        return "No computers configured.\n\nUse 'verdi computer setup' to add computers."

    if "process" in cmd_name.lower() and "No" in error:
        return "No processes found.\n\nSubmit calculations to see them here."

    return error or "Command failed"
