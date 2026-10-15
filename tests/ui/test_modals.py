"""Tests for modal dialogs."""

import pytest
from textual.widgets import Button

from verdideck.ui import ConfirmDialog, HelpModal


def test_help_modal_creation() -> None:
    """Test that help modal can be instantiated."""
    modal = HelpModal()
    assert modal is not None
    assert len(modal.BINDINGS) > 0


def test_help_modal_close_action() -> None:
    """Test help modal close action."""
    modal = HelpModal()
    # Mock dismiss method to verify it's called
    dismiss_called = False

    def mock_dismiss() -> None:
        nonlocal dismiss_called
        dismiss_called = True

    modal.dismiss = mock_dismiss  # type: ignore[assignment,method-assign]
    modal.action_close_help()
    assert dismiss_called


def test_confirm_dialog_creation() -> None:
    """Test that confirm dialog can be instantiated."""
    dialog = ConfirmDialog("Test Title", "Test message")
    assert dialog is not None
    assert dialog.title_text == "Test Title"
    assert dialog.message_text == "Test message"
    assert len(dialog.BINDINGS) >= 3  # y, n, escape


@pytest.mark.asyncio
async def test_confirm_dialog_button_yes() -> None:
    """Test confirm dialog yes button."""
    dialog = ConfirmDialog("Test", "Message")
    result = None

    def mock_dismiss(value: bool) -> None:
        nonlocal result
        result = value

    dialog.dismiss = mock_dismiss  # type: ignore[assignment,method-assign]

    # Create mock button event
    button = Button("Yes", id="yes")
    event = Button.Pressed(button)
    dialog.on_button_pressed(event)

    assert result is True


@pytest.mark.asyncio
async def test_confirm_dialog_button_no() -> None:
    """Test confirm dialog no button."""
    dialog = ConfirmDialog("Test", "Message")
    result = None

    def mock_dismiss(value: bool) -> None:
        nonlocal result
        result = value

    dialog.dismiss = mock_dismiss  # type: ignore[assignment,method-assign]

    # Create mock button event
    button = Button("No", id="no")
    event = Button.Pressed(button)
    dialog.on_button_pressed(event)

    assert result is False


def test_confirm_dialog_action_confirm() -> None:
    """Test confirm dialog confirm action."""
    dialog = ConfirmDialog("Test", "Message")
    result = None

    def mock_dismiss(value: bool) -> None:
        nonlocal result
        result = value

    dialog.dismiss = mock_dismiss  # type: ignore[assignment,method-assign]
    dialog.action_confirm()
    assert result is True


def test_confirm_dialog_action_cancel() -> None:
    """Test confirm dialog cancel action."""
    dialog = ConfirmDialog("Test", "Message")
    result = None

    def mock_dismiss(value: bool) -> None:
        nonlocal result
        result = value

    dialog.dismiss = mock_dismiss  # type: ignore[assignment,method-assign]
    dialog.action_cancel()
    assert result is False
