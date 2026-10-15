"""Pytest configuration and fixtures."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from verdideck.app import VerdiDeckApp


@pytest.fixture
def app() -> "VerdiDeckApp":
    """Create VerdiDeckApp instance for testing."""
    from verdideck.app import VerdiDeckApp

    return VerdiDeckApp()
