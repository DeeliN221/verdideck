"""Tests for command output formatters."""

from verdideck.commands.formatters import (
    format_process_list,
    format_table_output,
    no_format,
    strip_command_echo,
)


def test_strip_command_echo_removes_verdi_line() -> None:
    """Test that strip_command_echo removes trailing verdi command."""
    text = (
        "PK    Created    Process label\n----  ---------  ---------------\n\n$ verdi process list"
    )
    result = strip_command_echo(text)
    assert "$ verdi" not in result
    assert "PK    Created" in result


def test_strip_command_echo_preserves_text_without_echo() -> None:
    """Test that text without echo is preserved."""
    text = "PK    Created    Process label\n----  ---------  ---------------"
    result = strip_command_echo(text)
    assert result == text


def test_format_process_list_removes_command_and_trailing_empty_lines() -> None:
    """Test that format_process_list cleans up process list output."""
    text = """PK    Created    Process label    ♻    Process State    Process status
----  ---------  ---------------  ---  ---------------  ----------------

Total results: 0

Report: ♻ Processes marked with check-mark were not run but taken from the cache.
Report: Add the option `-P pk cached_from` to the command to display cache source.
Report: Last time an entry changed state: never
Report: Checking daemon load... OK
Report: Using 0% of the available daemon worker slots.

$ verdi process list"""

    result = format_process_list(text)

    # Should not contain command echo
    assert "$ verdi" not in result

    # Should contain table header
    assert "PK    Created" in result

    # Should contain reports
    assert "Total results: 0" in result
    assert "Report:" in result


def test_format_table_output_removes_command() -> None:
    """Test that format_table_output removes command echo."""
    text = """Label  Description
-----  -----------
test1  Test computer 1
test2  Test computer 2

$ verdi computer list"""

    result = format_table_output(text)

    assert "$ verdi" not in result
    assert "Label  Description" in result
    assert "test1" in result


def test_no_format_preserves_text() -> None:
    """Test that no_format returns text unchanged."""
    text = "Some text\nwith multiple\nlines\n$ verdi status"
    result = no_format(text)
    assert result == text


def test_format_process_list_with_empty_output() -> None:
    """Test format_process_list handles empty/minimal output."""
    text = "$ verdi process list"
    result = format_process_list(text)
    assert result == ""


def test_format_table_output_with_trailing_newlines() -> None:
    """Test that trailing newlines are removed."""
    text = """Label  Description
-----  -----------


$ verdi computer list"""

    result = format_table_output(text)

    assert "$ verdi" not in result
    # Should not end with multiple newlines
    assert not result.endswith("\n\n")
