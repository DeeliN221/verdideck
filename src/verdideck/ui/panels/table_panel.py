"""Table panel for displaying tabular data with interactive navigation."""

from collections.abc import Callable
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.message import Message
from textual.widgets import DataTable, Static

from verdideck.core.config import get_config_value


class TablePanel(Container):
    """Panel for displaying command output as interactive table (panels 1-6) with tab support.

    Uses DataTable for interactive table navigation with row-level selection.
    """

    # Allow this container to receive focus
    can_focus = True

    DEFAULT_CSS = """
    TablePanel {
        border: solid $primary;
    }

    TablePanel:focus-within {
        border: $accent;
    }

    TablePanel DataTable {
        border: none;
    }

    TablePanel .footer-text {
        height: auto;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
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
        tabs: list[
            tuple[
                str,
                Callable[..., Any],
                list[str],
                Optional[Callable[[str], str]],
                Callable[[str], dict[str, Any]],
            ]
        ],
    ) -> None:
        """Initialize table panel with multiple tabs.

        Args:
            panel_id: Panel number (1-6)
            tabs: List of (tab_name, command_func, args, formatter, parser) tuples.
                  - tab_name: Name displayed in tab header
                  - command_func: AiiDA command function to execute
                  - args: Arguments for the command
                  - formatter: Optional text formatter (applied before parser)
                  - parser: Parser to convert formatted text to table data
        """
        super().__init__(id=f"panel-{panel_id}")
        self._panel_id = panel_id
        self._tabs = tabs
        self._current_tab_index = 0
        self._tab_contents: dict[int, dict[str, Any]] = {}  # Cache table data for each tab
        self._data_table: Optional[DataTable] = None
        self._footer: Optional[Static] = None
        self._update_title()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        # Create DataTable
        zebra_stripes = get_config_value("table_zebra_stripes", True)
        self._data_table = DataTable(
            show_header=True,
            show_row_labels=False,
            zebra_stripes=zebra_stripes,
            cursor_type="row",
        )
        yield self._data_table

        # Create footer for displaying "Total results" etc.
        self._footer = Static("", classes="footer-text")
        yield self._footer

    def on_mount(self) -> None:
        """Handle mount event."""
        # Data table is ready for interaction
        pass

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
    ) -> tuple[
        Callable[..., Any],
        list[str],
        Optional[Callable[[str], str]],
        Callable[[str], dict[str, Any]],
    ]:
        """Get current tab's command function, args, formatter, and parser.

        Returns:
            Tuple of (command_func, args, formatter, parser)
        """
        if not self._tabs:
            raise ValueError("No tabs configured")
        tab_info = self._tabs[self._current_tab_index]
        _tab_name, cmd_func, args, formatter, parser = tab_info
        return cmd_func, args, formatter, parser

    def update_content(self, table_data: dict[str, Any]) -> None:
        """Update current tab's content with table data.

        Args:
            table_data: Dictionary with keys:
                        - "headers": List of column headers
                        - "rows": List of row data (each row is a list of cell values)
                        - "footer": Footer text (like "Total results: X")
        """
        self._tab_contents[self._current_tab_index] = table_data

        if self._data_table is None:
            return

        # Clear existing data including columns
        self._data_table.clear(columns=True)

        # Add columns
        headers = table_data.get("headers", [])
        if headers:
            self._data_table.add_columns(*headers)

        # Add rows
        rows = table_data.get("rows", [])
        for row in rows:
            # Ensure row has same length as headers
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[: len(headers)]
            self._data_table.add_row(*row)

        # Update footer
        footer = table_data.get("footer", "")
        if self._footer:
            self._footer.update(footer)

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
                self.update_content(self._tab_contents[self._current_tab_index])
            else:
                # Clear table and show loading in footer
                if self._data_table:
                    self._data_table.clear()
                if self._footer:
                    self._footer.update("Loading...")
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
                self.update_content(self._tab_contents[self._current_tab_index])
            else:
                # Clear table and show loading in footer
                if self._data_table:
                    self._data_table.clear()
                if self._footer:
                    self._footer.update("Loading...")
            self.post_message(self.TabChanged(self.id or "", self._current_tab_index))
            return True
        return False

    def focus(self, scroll_visible: bool = True) -> "TablePanel":
        """Override focus to delegate to DataTable for keyboard navigation."""
        self.post_message(self.Focused(self.id or ""))
        # Delegate focus to the data table to enable keyboard navigation
        if self._data_table is not None:
            self._data_table.focus(scroll_visible)
        return self

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
        # Let other keys pass through to DataTable for navigation
