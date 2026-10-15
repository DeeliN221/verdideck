"""Text formatters for command outputs."""


def strip_command_echo(text: str) -> str:
    """Remove trailing command echo line (e.g., '$ verdi process list').

    Args:
        text: Raw command output

    Returns:
        Text with command echo removed
    """
    # Remove last line if it starts with '$ verdi'
    lines = text.splitlines()
    if lines and lines[-1].strip().startswith("$ verdi"):
        return "\n".join(lines[:-1])
    return text


def format_process_list(text: str) -> str:
    """Format process list output.

    - Removes command echo
    - Keeps table and useful reports

    Args:
        text: Raw process list output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)

    # Split into lines for processing
    lines = text.splitlines()

    # Remove empty lines at the end
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)


def format_table_output(text: str) -> str:
    """Format generic table output (for computer, code, group, node lists).

    - Removes command echo
    - Preserves table structure

    Args:
        text: Raw table output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)

    # Remove trailing empty lines
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)


def format_daemon_status(text: str) -> str:
    """Format daemon status output.

    Args:
        text: Raw daemon status output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)
    return text.strip()


def format_storage_info(text: str) -> str:
    """Format storage info output.

    Args:
        text: Raw storage info output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)
    return text.strip()


def format_config_list(text: str) -> str:
    """Format config list output.

    Args:
        text: Raw config list output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)
    return text.strip()


def format_profile_list(text: str) -> str:
    """Format profile list output.

    Args:
        text: Raw profile list output

    Returns:
        Formatted text
    """
    # Remove command echo
    text = strip_command_echo(text)
    return text.strip()


# No formatter needed (returns text as-is)
def no_format(text: str) -> str:
    """Pass through text without formatting.

    Args:
        text: Input text

    Returns:
        Same text unchanged
    """
    return text
