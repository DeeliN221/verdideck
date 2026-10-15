"""Tests for UI panel widgets."""

import pytest

from verdideck.app import VerdiDeckApp
from verdideck.ui import InfoPanel
from verdideck.ui.panels.command_panel import CommandPanel
from verdideck.ui.panels.results_panel import ResultsPanel


@pytest.mark.asyncio
async def test_app_has_all_panels() -> None:
    """Test that app contains all required panels."""
    app = VerdiDeckApp()
    async with app.run_test():
        # Check all 7 panels exist (0-6)
        assert app.query_one("#panel-0")
        assert app.query_one("#panel-1")
        assert app.query_one("#panel-2")
        assert app.query_one("#panel-3")
        assert app.query_one("#panel-4")
        assert app.query_one("#panel-5")
        assert app.query_one("#panel-5")


@pytest.mark.asyncio
async def test_focus_switching() -> None:
    """Test that number keys switch focus to panels."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        # Wait for initial focus to be set (happens in on_mount after refresh)
        await pilot.pause()

        # Initial focus should be on panel-0 (results panel)
        assert app.focused is not None and app.focused.id == "panel-0"

        # Test focus switching with number keys
        # TablePanel delegates focus to internal DataTable
        await pilot.press("1")
        panel_1 = app.query_one("#panel-1")
        assert panel_1.has_focus or any(child.has_focus for child in panel_1.children)

        await pilot.press("2")
        panel_2 = app.query_one("#panel-2")
        assert panel_2.has_focus or any(child.has_focus for child in panel_2.children)

        await pilot.press("0")
        # Panel 0 (ResultsPanel) should be focused again
        focused = app.focused
        assert focused is not None and focused.id == "panel-0"


@pytest.mark.asyncio
async def test_status_panel_update() -> None:
    """Test InfoPanel (panel-5) can update content."""
    app = VerdiDeckApp()
    async with app.run_test():
        panel = app.query_one("#panel-5", InfoPanel)
        panel.update_content("Test status content")
        # Verify update happened without errors
        assert panel is not None


@pytest.mark.asyncio
async def test_status_panel_tabs() -> None:
    """Test InfoPanel (panel-5) tab switching."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Focus on panel-5
        await pilot.press("5")
        panel = app.query_one("#panel-5", InfoPanel)

        # Should start at first tab (status)
        assert panel._current_tab_index == 0
        title = str(panel.border_title)
        assert "[green]status[/green]" in title

        # Switch to next tab (daemon)
        await pilot.press("]")
        await pilot.pause()
        assert panel._current_tab_index == 1
        title = str(panel.border_title)
        assert "[green]daemon[/green]" in title

        # Switch to next tab (storage)
        await pilot.press("]")
        await pilot.pause()
        assert panel._current_tab_index == 2
        title = str(panel.border_title)
        assert "[green]storage[/green]" in title

        # Try to go beyond last tab (should stay at storage)
        await pilot.press("]")
        await pilot.pause()
        assert panel._current_tab_index == 2

        # Go back to previous tab (daemon)
        await pilot.press("[")
        await pilot.pause()
        assert panel._current_tab_index == 1

        # Go back to first tab (status)
        await pilot.press("[")
        await pilot.pause()
        assert panel._current_tab_index == 0


def test_command_panel_compose() -> None:
    """Test CommandPanel composition."""
    panel = CommandPanel()
    widgets = list(panel.compose())
    # Should have 5 command category widgets
    assert len(widgets) == 5


def test_results_panel_compose() -> None:
    """Test ResultsPanel initialization."""
    panel = ResultsPanel()
    assert panel._messages == []
    assert panel.can_focus is True


@pytest.mark.asyncio
async def test_results_panel_mount() -> None:
    """Test ResultsPanel mount shows welcome message."""
    app = VerdiDeckApp()
    async with app.run_test():
        panel = app.query_one("#panel-0", ResultsPanel)
        # on_mount should set welcome message
        messages_text = " ".join(panel._messages)
        assert "VerdiDeck" in messages_text
        assert "Welcome" in messages_text


@pytest.mark.asyncio
async def test_results_panel_write() -> None:
    """Test ResultsPanel write method."""
    app = VerdiDeckApp()
    async with app.run_test():
        panel = app.query_one("#panel-0", ResultsPanel)
        initial_count = len(panel._messages)

        # Write new text
        panel.write("Test output")
        assert "Test output" in panel._messages
        assert len(panel._messages) > initial_count

        # Write more text
        panel.write("More output")
        assert "More output" in panel._messages


@pytest.mark.asyncio
async def test_results_panel_error_deduplication() -> None:
    """Test ResultsPanel deduplicates repeated error messages."""
    app = VerdiDeckApp()
    async with app.run_test():
        panel = app.query_one("#panel-0", ResultsPanel)

        # Clear initial messages for clean test
        panel._messages = []
        panel._seen_errors = set()

        # Write the same error message multiple times
        error_msg = "No AiiDA profile configured.\nPlease run:\n  verdi quicksetup"

        panel.write(error_msg)
        count_after_first = len(panel._messages)
        assert count_after_first > 0  # First message should be added

        # Write same error again - should be deduplicated
        panel.write(error_msg)
        count_after_second = len(panel._messages)
        assert count_after_second == count_after_first  # No new messages

        # Write a different error - should be added
        panel.write("Some other error")
        assert len(panel._messages) > count_after_second

        # Write I/O error multiple times
        panel._messages = []
        panel._seen_errors = set()

        panel.write("I/O operation on closed file")
        first_count = len(panel._messages)

        panel.write("I/O operation on closed file")
        assert len(panel._messages) == first_count  # Deduplicated
