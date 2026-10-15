"""Information display panels (1-5)."""

from collections.abc import Callable
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.message import Message
from textual.widgets import DataTable

from verdideck.core.config import get_config_value


class InfoPanel(Container):
    """Panel for displaying command output (panels 1-5) with tab support.

    Uses DataTable for interactive display with cell selection.
    """

    # Allow this container to receive focus
    can_focus = True

    DEFAULT_CSS = """
    InfoPanel {
        border: solid $primary;
    }

    InfoPanel:focus-within {
        border: $accent;
    }

    InfoPanel DataTable {
        border: none;
    }
    """

    class Focused(Message):
        """Posted when panel gains focus."""

        def __init__(self, panel_id: str) -> None:
            """Initialize message.

            Args:
                panel_id: ID of the focused panel
            """
            super().__init__()
            self.panel_id = panel_id

    class TabChanged(Message):
        """Posted when tab is changed."""

        def __init__(self, panel_id: str, tab_index: int) -> None:
            """Initialize message.

            Args:
                panel_id: ID of the panel
                tab_index: Index of the new active tab
            """
            super().__init__()
            self.panel_id = panel_id
            self.tab_index = tab_index

    def __init__(
        self,
        panel_id: int,
        tabs: list[tuple[str, Callable[..., Any], list[str], Optional[Callable[[str], str]]]],
    ) -> None:
        """Initialize info panel with multiple tabs.

        Args:
            panel_id: Panel number (4-6) for text-based panels
            tabs: List of (tab_name, command_func, args, formatter) tuples
        """
        super().__init__(id=f"panel-{panel_id}")
        self._panel_id = panel_id
        self._tabs = tabs
        self._current_tab_index = 0
        self._tab_contents: dict[int, list[str]] = {}  # Cache content lines for each tab
        self._data_table: Optional[DataTable] = None
        self._update_title()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        zebra_stripes = get_config_value("table_zebra_stripes", True)
        self._data_table = DataTable(
            show_header=False,
            show_row_labels=False,
            zebra_stripes=zebra_stripes,
            cursor_type="cell",
        )
        yield self._data_table

    def _update_title(self) -> None:
        """Update border title to show all tabs with current tab highlighted."""
        if not self._tabs:
            return

        # Build title with all tab names, highlighting the current one
        tab_parts = []
        for i, tab_info in enumerate(self._tabs):
            tab_name = tab_info[0]
            if i == self._current_tab_index:
                tab_parts.append(f"[green]{tab_name}[/green]")
            else:
                tab_parts.append(tab_name)

        # Join tabs with slash separator
        tabs_display = "/".join(tab_parts)
        self.border_title = f"[{self._panel_id}] {tabs_display}"

    def get_current_tab_command(
        self,
    ) -> tuple[Callable[..., Any], list[str], Optional[Callable[[str], str]]]:
        """Get current tab's command function, args, and formatter.

        Returns:
            Tuple of (command_func, args, formatter)
        """
        if not self._tabs:
            raise ValueError("No tabs configured")
        tab_info = self._tabs[self._current_tab_index]
        _, cmd_func, args, formatter = tab_info
        return cmd_func, args, formatter

    def update_content(self, text: str) -> None:
        """Update current tab's content.

        Args:
            text: New content to display
        """
        if not self._data_table:
            return

        # Split text into lines and filter
        lines = text.split("\n")
        filtered_lines = self._filter_content_lines(lines)
        self._tab_contents[self._current_tab_index] = filtered_lines

        # Rebuild table
        self._data_table.clear(columns=True)
        self._data_table.add_column("Content", width=None)

        for line in filtered_lines:
            if line:  # Skip empty lines
                self._data_table.add_row(line)

    def next_tab(self) -> bool:
        """Switch to next tab.

        Returns:
            True if tab was changed, False if already at last tab
        """
        if self._current_tab_index < len(self._tabs) - 1:
            self._current_tab_index += 1
            self._update_title()
            # Restore cached content if available
            if self._current_tab_index in self._tab_contents:
                self._rebuild_table()
            else:
                self._show_loading()
            self.post_message(self.TabChanged(self.id or "", self._current_tab_index))
            return True
        return False

    def prev_tab(self) -> bool:
        """Switch to previous tab.

        Returns:
            True if tab was changed, False if already at first tab
        """
        if self._current_tab_index > 0:
            self._current_tab_index -= 1
            self._update_title()
            # Restore cached content if available
            if self._current_tab_index in self._tab_contents:
                self._rebuild_table()
            else:
                self._show_loading()
            self.post_message(self.TabChanged(self.id or "", self._current_tab_index))
            return True
        return False

    def focus(self, scroll_visible: bool = True) -> "InfoPanel":
        """Override focus to make this panel focusable."""
        self.post_message(self.Focused(self.id or ""))
        return super().focus(scroll_visible)

    async def _on_key(self, event: Key) -> None:
        """Handle key events for tab switching.

        Args:
            event: Key event
        """
        # Handle tab switching keys
        if event.key == "left_square_bracket":  # [
            event.prevent_default()
            event.stop()
            if self.prev_tab():
                # Call the refresh method that exists on the app
                if hasattr(self.app, "_refresh_current_panel"):
                    self.app._refresh_current_panel()  # type: ignore
        elif event.key == "right_square_bracket":  # ]
            event.prevent_default()
            event.stop()
            if self.next_tab():
                # Call the refresh method that exists on the app
                if hasattr(self.app, "_refresh_current_panel"):
                    self.app._refresh_current_panel()  # type: ignore
        # Let other keys pass through for normal navigation

    def _rebuild_table(self) -> None:
        """Rebuild table from cached content."""
        if not self._data_table:
            return

        lines = self._tab_contents.get(self._current_tab_index, [])
        self._data_table.clear(columns=True)
        self._data_table.add_column("Content", width=None)

        for line in lines:
            if line:
                self._data_table.add_row(line)

    def _show_loading(self) -> None:
        """Show loading message in table."""
        if not self._data_table:
            return

        self._data_table.clear(columns=True)
        self._data_table.add_column("Content", width=None)
        self._data_table.add_row("Loading...")

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

            # Skip "Usage:" lines from help text
            if stripped.startswith("Usage:"):
                continue

            # Keep this line
            filtered.append(line.rstrip())

        return filtered
