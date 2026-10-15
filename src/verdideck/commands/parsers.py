"""Parsers to convert command text output to structured data."""

import re
from typing import Any


def parse_table(text: str) -> dict[str, Any]:
    """Parse text table output into structured data.

    Handles tables with format:
    ```
    Column1  Column2  Column3
    -------  -------  -------
    value1   value2   value3
    value4   value5   value6
    ```

    Args:
        text: Text containing table data

    Returns:
        Dictionary with:
        - "headers": List of column headers
        - "rows": List of row data (each row is a list of cell values)
        - "footer": Any text after the table (like "Total results: X")
    """
    lines = text.strip().splitlines()
    if not lines:
        return {"headers": [], "rows": [], "footer": ""}

    # Find the separator line (usually dashes)
    separator_idx = -1
    for i, line in enumerate(lines):
        # Separator line should be mostly dashes and spaces
        if re.match(r"^[\s\-]+$", line):
            separator_idx = i
            break

    if separator_idx == -1:
        # No separator found - treat as plain text
        return {"headers": [], "rows": [], "footer": text}

    # Extract headers (line before separator)
    if separator_idx == 0:
        headers = []
    else:
        header_line = lines[separator_idx - 1]
        # Split by multiple spaces (2 or more)
        headers = [h.strip() for h in re.split(r"\s{2,}", header_line) if h.strip()]

    # Extract data rows (lines after separator)
    rows = []
    footer_lines = []
    in_footer = False

    for i in range(separator_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # Check if we've reached the footer section
        # Footer typically starts with empty lines or "Total", "Report:", etc.
        if not stripped or stripped.startswith(
            ("Total", "Report:", "Info:", "Warning:", "Error:", "Success:", "Critical:", "Debug:")
        ):
            in_footer = True

        if in_footer:
            # Filter footer lines - skip Report/Info/Warning/etc. prefixed lines
            if stripped and not re.match(r"^(Report|Info|Warning|Error|Debug|Critical):", stripped):
                footer_lines.append(stripped)
        else:
            # Parse data row - split by multiple spaces
            cells = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
            if cells:  # Only add non-empty rows
                rows.append(cells)

    footer = "\n".join(footer_lines) if footer_lines else ""

    return {"headers": headers, "rows": rows, "footer": footer}


def parse_process_list(text: str) -> dict[str, Any]:
    """Parse verdi process list output.

    Args:
        text: Process list output

    Returns:
        Structured table data
    """
    return parse_table(text)


def parse_computer_list(text: str) -> dict[str, Any]:
    """Parse verdi computer list output.

    Args:
        text: Computer list output (format: "* computer_name")

    Returns:
        Structured table data with "label" header
    """
    lines = text.strip().splitlines()
    rows = []

    for line in lines:
        stripped = line.strip()
        # Skip empty lines and Report/Info lines
        if not stripped or stripped.startswith(
            ("Report:", "Info:", "Warning:", "Error:", "Success:", "Critical:", "Debug:")
        ):
            continue

        # Extract computer name (remove leading "* ")
        if stripped.startswith("* "):
            computer_name = stripped[2:].strip()
            rows.append([computer_name])
        elif stripped:
            # In case there's no "* " prefix
            rows.append([stripped])

    return {
        "headers": ["label"],
        "rows": rows,
        "footer": "",
    }


def parse_code_list(text: str) -> dict[str, Any]:
    """Parse verdi code list output.

    Args:
        text: Code list output

    Returns:
        Structured table data
    """
    return parse_table(text)


def parse_group_list(text: str) -> dict[str, Any]:
    """Parse verdi group list output.

    Args:
        text: Group list output

    Returns:
        Structured table data
    """
    return parse_table(text)


def parse_node_list(text: str) -> dict[str, Any]:
    """Parse verdi node list output.

    Args:
        text: Node list output

    Returns:
        Structured table data
    """
    return parse_table(text)


def parse_plugin_list(text: str) -> dict[str, Any]:
    """Parse verdi plugin list output.

    Args:
        text: Plugin list output (format: "* plugin.entry.point")

    Returns:
        Structured table data with "entry point" header
    """
    lines = text.strip().splitlines()
    rows = []

    for line in lines:
        stripped = line.strip()
        # Skip empty lines, header lines, and Report/Info lines
        if not stripped or stripped.startswith(
            (
                "Registered entry points",
                "Report:",
                "Info:",
                "Warning:",
                "Error:",
                "Success:",
                "Critical:",
                "Debug:",
            )
        ):
            continue

        # Extract plugin name (remove leading "* ")
        if stripped.startswith("* "):
            plugin_name = stripped[2:].strip()
            rows.append([plugin_name])
        elif stripped:
            # In case there's no "* " prefix
            rows.append([stripped])

    return {
        "headers": ["entry point"],
        "rows": rows,
        "footer": "",
    }


def parse_calcjob_help(text: str) -> dict[str, Any]:
    """Parse verdi calcjob --help output to extract subcommands.

    Args:
        text: Help text from verdi calcjob --help

    Returns:
        Structured table data with "command" and "description" headers
    """
    lines = text.strip().splitlines()
    rows = []
    in_commands_section = False

    for line in lines:
        stripped = line.strip()

        # Detect Commands: section
        if stripped.startswith("Commands:"):
            in_commands_section = True
            continue

        # Stop at Options: or other sections
        if in_commands_section and (not line.startswith("  ") or stripped.startswith("-")):
            break

        # Parse command lines (format: "  command_name  Description text")
        if in_commands_section and line.startswith("  ") and not stripped.startswith("-"):
            # Split by multiple spaces (2 or more)
            parts = [p.strip() for p in re.split(r"\s{2,}", line.strip()) if p.strip()]
            if len(parts) >= 2:
                command_name = parts[0]
                description = parts[1]
                rows.append([command_name, description])
            elif len(parts) == 1:
                # Command without description
                rows.append([parts[0], ""])

    return {
        "headers": ["command", "description"],
        "rows": rows,
        "footer": "",
    }
