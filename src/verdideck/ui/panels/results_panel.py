"""Results panel for displaying command outputs."""

from typing import Any, Optional

import pyperclip
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.widgets import DataTable

from verdideck.core.config import get_config_value


class ResultsPanel(Container):
    """Panel [0] for showing command results.

    Uses DataTable for interactive display with cell selection.
    """

    # Allow this container to receive focus
    can_focus = True

    DEFAULT_CSS = """
    ResultsPanel {
        height: 80%;
        border: solid $primary;
    }

    ResultsPanel:focus-within {
        border: $accent;
    }

    ResultsPanel DataTable {
        border: none;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize results panel."""
        super().__init__(**kwargs)
        self.border_title = "[0] details"
        self._data_table: Optional[DataTable] = None
        self._messages: list[str] = []
        self._seen_errors: set[str] = set()  # Track unique error messages
        self._selection_mode: bool = False  # Visual selection mode
        self._selected_rows: set[int] = set()  # Track selected row indices
        self._selection_start: Optional[int] = None  # Start of current selection range

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        zebra_stripes = get_config_value("table_zebra_stripes", True)
        self._data_table = DataTable(
            show_header=True,
            show_row_labels=False,
            zebra_stripes=zebra_stripes,
            cursor_type="cell",
        )
        yield self._data_table

    def on_mount(self) -> None:
        """Display welcome message on startup."""
        show_welcome = get_config_value("show_welcome_message", True)
        if show_welcome and self._data_table:
            self._data_table.add_column("Message", width=None)
            self._data_table.add_row("VerdiDeck v1.0.4")
            self._data_table.add_row("Welcome! Press ? for help")
            self._messages = ["VerdiDeck v1.0.4", "Welcome! Press ? for help"]

    async def _on_key(self, event: Key) -> None:
        """Handle key events for selection and copy operations.

        Args:
            event: Key event
        """
        if event.key == "v":
            # Toggle selection mode
            event.prevent_default()
            event.stop()
            self._toggle_selection_mode()
        elif event.key == "c":
            # Copy selected rows
            event.prevent_default()
            event.stop()
            self._copy_selected_rows()
        elif self._selection_mode and event.key in ("up", "down", "j", "k"):
            # Update selection when navigating in visual mode
            # Let the event propagate to move cursor, then update selection
            self.set_timer(0.01, self._update_selection_from_cursor)

    def _update_selection_from_cursor(self) -> None:
        """Update selected rows based on current cursor position."""
        if not self._data_table or not self._selection_mode or self._selection_start is None:
            return

        cursor_row = self._data_table.cursor_row
        if cursor_row < 0:
            return

        # Select all rows between start and current cursor
        start = min(self._selection_start, cursor_row)
        end = max(self._selection_start, cursor_row)
        self._selected_rows = set(range(start, end + 1))

        # Update title to show selection count
        count = len(self._selected_rows)
        self.border_title = f"[0] details -- VISUAL ({count} lines) --"

    def _toggle_selection_mode(self) -> None:
        """Toggle visual selection mode."""
        if not self._data_table:
            return

        self._selection_mode = not self._selection_mode

        if self._selection_mode:
            # Entering selection mode - mark current cursor position as selection start
            cursor_row = self._data_table.cursor_row
            if cursor_row >= 0:
                self._selection_start = cursor_row
                self._selected_rows = {cursor_row}
            self.border_title = "[0] details -- VISUAL (1 lines) --"
        else:
            # Exiting selection mode - clear selection
            self._selection_start = None
            self._selected_rows.clear()
            self.border_title = "[0] details"

    def _copy_selected_rows(self) -> None:
        """Copy selected rows to clipboard."""
        if not self._data_table or not self._selected_rows:
            return

        # Get messages for selected row indices
        selected_messages = []
        for row_idx in sorted(self._selected_rows):
            if 0 <= row_idx < len(self._messages):
                selected_messages.append(self._messages[row_idx])

        if selected_messages:
            # Copy to clipboard
            content = "\n".join(selected_messages)
            try:
                pyperclip.copy(content)
                # Provide feedback - temporarily update title
                original_title = self.border_title
                self.border_title = f"[0] details -- Copied {len(selected_messages)} lines --"
                # Reset title after a moment
                self.set_timer(1.0, lambda: setattr(self, "border_title", original_title))
            except Exception:
                # If clipboard fails, silently ignore
                pass

    def write(self, text: str, dedupe: bool = True) -> None:
        """Append text to the panel (for compatibility with RichLog interface).

        Args:
            text: Text to append
            dedupe: If True, skip duplicate error messages (default True)
        """
        if not self._data_table:
            return

        # Check for duplicate error messages to avoid spam
        if dedupe:
            # Normalize text for comparison (strip whitespace, lowercase)
            normalized = text.strip().lower()
            # Check if this is a known repeated error pattern
            if self._is_duplicate_error(normalized):
                return
            # Mark this error as seen
            self._mark_error_seen(normalized)

        # Split multi-line text into separate rows and filter
        lines = text.split("\n")
        filtered = self._filter_content_lines(lines)
        self._messages.extend(filtered)

        # Rebuild table with all messages
        self._rebuild_table()

    def _is_duplicate_error(self, normalized_text: str) -> bool:
        """Check if this is a duplicate error message.

        Args:
            normalized_text: Lowercase, stripped text

        Returns:
            True if this error has been seen before
        """
        # Common error patterns that should only appear once
        error_patterns = [
            "no aiida profile configured",
            "i/o operation on closed file",
            "please run:",
            "verdi quicksetup",
            "verdi setup",
        ]

        for pattern in error_patterns:
            if pattern in normalized_text:
                # Check if we've seen any error with this pattern
                if pattern in self._seen_errors:
                    return True
        return False

    def _mark_error_seen(self, normalized_text: str) -> None:
        """Mark an error pattern as seen.

        Args:
            normalized_text: Lowercase, stripped text
        """
        error_patterns = [
            "no aiida profile configured",
            "i/o operation on closed file",
            "please run:",
            "verdi quicksetup",
            "verdi setup",
        ]

        for pattern in error_patterns:
            if pattern in normalized_text:
                self._seen_errors.add(pattern)

    def _rebuild_table(self) -> None:
        """Rebuild the table with current messages."""
        if not self._data_table:
            return

        self._data_table.clear(columns=True)
        self._data_table.add_column("Message", width=None)

        for msg in self._messages:
            self._data_table.add_row(msg)

    def _filter_content_lines(self, lines: list[str]) -> list[str]:
        """Filter out non-content lines like Report:, separators, etc.

        Args:
            lines: Original lines from command output

        Returns:
            Filtered list of content lines
        """
        import re

        filtered = []
        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Skip separator lines (mostly dashes and spaces)
            if re.match(r"^[\s\-]+$", stripped):
                continue

            # Skip Report/Info/Warning/Error prefixed lines
            if re.match(r"^(Report|Info|Warning|Error|Total|Success|Critical|Debug):", stripped):
                continue

            # Skip command echo lines
            if stripped.startswith("$ verdi"):
                continue

            # Keep this line
            filtered.append(line.rstrip())

        return filtered
