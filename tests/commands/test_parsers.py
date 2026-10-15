"""Tests for command output parsers."""

from verdideck.commands.parsers import (
    parse_calcjob_help,
    parse_computer_list,
    parse_plugin_list,
    parse_table,
)


def test_parse_computer_list_with_computers() -> None:
    """Test parsing computer list with multiple computers."""
    text = """Report: List of configured computers
Report: Use 'verdi computer show COMPUTERLABEL' to display more detailed information
* localhost
* nm
"""
    result = parse_computer_list(text)

    assert result["headers"] == ["label"]
    assert len(result["rows"]) == 2
    assert result["rows"][0] == ["localhost"]
    assert result["rows"][1] == ["nm"]
    assert result["footer"] == ""


def test_parse_computer_list_empty() -> None:
    """Test parsing empty computer list."""
    text = """Report: List of configured computers
Report: Use 'verdi computer show COMPUTERLABEL' to display more detailed information
"""
    result = parse_computer_list(text)

    assert result["headers"] == ["label"]
    assert len(result["rows"]) == 0
    assert result["footer"] == ""


def test_parse_plugin_list_with_plugins() -> None:
    """Test parsing plugin list with multiple plugins."""
    text = """Registered entry points for aiida.calculations:
* core.arithmetic.add
* core.stash
* core.templatereplacer
* core.transfer

Report: Pass the entry point as an argument to display detailed information
"""
    result = parse_plugin_list(text)

    assert result["headers"] == ["entry point"]
    assert len(result["rows"]) == 4
    assert result["rows"][0] == ["core.arithmetic.add"]
    assert result["rows"][1] == ["core.stash"]
    assert result["footer"] == ""


def test_parse_plugin_list_empty() -> None:
    """Test parsing empty plugin list."""
    text = """Registered entry points for aiida.calculations:

Report: Pass the entry point as an argument to display detailed information
"""
    result = parse_plugin_list(text)

    assert result["headers"] == ["entry point"]
    assert len(result["rows"]) == 0
    assert result["footer"] == ""


def test_parse_table_with_headers() -> None:
    """Test parsing standard table with headers and separator."""
    text = """Full label      Pk  Entry point
------------  ----  -------------------
dspaw@nm         1  core.code.installed

Use `verdi code show IDENTIFIER` to see details for a code
"""
    result = parse_table(text)

    assert len(result["headers"]) == 3
    assert "Full label" in result["headers"]
    assert "Pk" in result["headers"]
    assert len(result["rows"]) == 1
    assert result["rows"][0][0] == "dspaw@nm"
    assert result["rows"][0][1] == "1"


def test_parse_table_without_separator() -> None:
    """Test that parse_table handles text without separator."""
    text = """Some plain text
without any table structure
"""
    result = parse_table(text)

    assert result["headers"] == []
    assert result["rows"] == []
    # Footer keeps the original text as-is (including trailing newline from the input)
    assert "Some plain text" in result["footer"]
    assert "without any table structure" in result["footer"]


def test_parse_calcjob_help() -> None:
    """Test parsing calcjob --help output."""
    text = """Usage: verdi calcjob [OPTIONS] COMMAND [ARGS]...

  Inspect and manage calcjobs.

Options:
  -v, --verbosity [notset|debug|info|report|warning|error|critical]
                                  Set the verbosity of the output.
  -h, --help                      Show this message and exit.

Commands:
  cleanworkdir  Clean all content of all output remote folders of calcjobs.
  gotocomputer  Open a shell in the remote folder on the calcjob.
  inputcat      Show the contents of one of the calcjob input files.
  inputls       Show the list of the generated calcjob input files.
"""
    result = parse_calcjob_help(text)

    assert result["headers"] == ["command", "description"]
    assert len(result["rows"]) == 4
    assert result["rows"][0] == [
        "cleanworkdir",
        "Clean all content of all output remote folders of calcjobs.",
    ]
    assert result["rows"][1] == [
        "gotocomputer",
        "Open a shell in the remote folder on the calcjob.",
    ]
    assert result["footer"] == ""
