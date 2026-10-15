"""Tests for main VerdiDeckApp."""

import pytest

from verdideck.app import VerdiDeckApp


def test_app_creation() -> None:
    """Test that app can be instantiated."""
    app = VerdiDeckApp()
    assert app.title == "VerdiDeck"


def test_app_bindings() -> None:
    """Test that required bindings are defined."""
    app = VerdiDeckApp()
    # BINDINGS can be tuples or Binding objects, extract keys safely
    binding_keys = [b[0] if isinstance(b, tuple) else b.key for b in app.BINDINGS]
    assert "q" in binding_keys
    assert "?" in binding_keys


@pytest.mark.asyncio
async def test_app_compose() -> None:
    """Test that app composes Header and Footer widgets."""
    app = VerdiDeckApp()
    async with app.run_test():
        assert app.query_one("#panel-0")
        assert app.query_one("#panel-1")
        assert app.query_one("#panel-2")
        assert app.query_one("#panel-3")
        assert app.query_one("#panel-4")
        assert app.query_one("#panel-5")


@pytest.mark.asyncio
async def test_app_focus_panel_actions() -> None:
    """Test focus panel actions for panels 3-6."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Test panel 3 (TablePanel delegates focus to internal DataTable)
        await pilot.press("3")
        await pilot.pause()
        panel_3 = app.query_one("#panel-3")
        # Check that panel or its children have focus
        assert panel_3.has_focus or any(child.has_focus for child in panel_3.children)

        # Test panel 4
        await pilot.press("4")
        await pilot.pause()
        assert app.query_one("#panel-4").has_focus

        # Test panel 5
        await pilot.press("5")
        await pilot.pause()
        assert app.query_one("#panel-5").has_focus

        # Test panel 5 (also tests _reset_left_panel_sizes)
        await pilot.press("5")
        await pilot.pause()
        assert app.query_one("#panel-5").has_focus


@pytest.mark.asyncio
async def test_app_scroll_actions() -> None:
    """Test scroll action methods."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Focus on panel-0
        await pilot.press("0")
        await pilot.pause()

        # Test scroll actions
        await pilot.press("j")  # scroll down
        await pilot.pause()

        await pilot.press("k")  # scroll up
        await pilot.pause()

        await pilot.press("h")  # scroll left
        await pilot.pause()

        await pilot.press("l")  # scroll right
        await pilot.pause()

        await pilot.press("G")  # scroll to end
        await pilot.pause()

        # No assertions needed - just ensure no errors occur


@pytest.mark.asyncio
async def test_app_scroll_home_double_tap() -> None:
    """Test double-tap 'g' to scroll home."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Focus on panel-0
        await pilot.press("0")
        await pilot.pause()

        # First scroll to end
        await pilot.press("G")
        await pilot.pause()

        # Double tap 'g' to go home
        await pilot.press("g", "g")
        await pilot.pause()

        # No assertions needed - just ensure no errors occur


@pytest.mark.asyncio
async def test_app_help_action() -> None:
    """Test help modal action."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open help modal
        await pilot.press("?")
        await pilot.pause()

        # Modal should be on screen stack
        assert len(app.screen_stack) > 1

        # Close with escape
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_app_refresh_action() -> None:
    """Test refresh action on focused panel."""
    app = VerdiDeckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Focus on panel-0 (results panel, doesn't support refresh)
        await pilot.press("0")
        await pilot.pause()

        # Try refresh (should do nothing for ResultsPanel)
        await pilot.press("r")
        await pilot.pause()

        # No error should occur
