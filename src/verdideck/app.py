"""Main Textual application entry point."""

import asyncio
import time
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from verdideck.commands import PANEL_TABS, TABLE_TABS, format_error_message
from verdideck.core import CommandRunner
from verdideck.core.batch_loader import load_all_startup_data
from verdideck.core.config import get_config_value
from verdideck.ui import InfoPanel, ResultsPanel, TablePanel


class VerdiDeckApp(App):
    """Keyboard-driven TUI for AiiDA verdi commands."""

    TITLE = "VerdiDeck"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
        Binding("escape", "pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("j", "scroll_down", "Down"),
        Binding("k", "scroll_up", "Up"),
        Binding("h", "scroll_left", "Left"),
        Binding("l", "scroll_right", "Right"),
        Binding("left", "scroll_left", "Left"),
        Binding("right", "scroll_right", "Right"),
        Binding("g", "scroll_home_trigger", "Top (gg)"),
        Binding("G", "scroll_end", "Bottom"),
        Binding("[", "prev_tab", "Prev Tab"),
        Binding("]", "next_tab", "Next Tab"),
        Binding("0", "focus_results", "Results"),
        Binding("1", "focus_panel_1", "Computer/Code/Plugin"),
        Binding("2", "focus_panel_2", "Process/CalcJob"),
        Binding("3", "focus_panel_3", "Group/Node"),
        Binding("4", "focus_panel_4", "Config/Profile"),
        Binding("5", "focus_panel_5", "Status"),
        Binding("a", "toggle_auto_refresh", "Auto-refresh"),
    ]

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize app."""
        super().__init__(*args, **kwargs)
        self._runner = CommandRunner()
        self._last_g_time: float = 0.0
        self._background_tasks: set = set()
        self._auto_refresh_enabled: bool = get_config_value("auto_refresh_on_startup", True)
        self._auto_refresh_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        # Cache for batch-loaded startup data
        self._startup_data_cache: dict[str, dict[str, Any]] = {}
        # Track which tabs have been loaded (for lazy loading)
        self._loaded_tabs: set[tuple[str, str]] = set()  # (panel_id, tab_name)

    CSS = """
#right-panels {
    width: 60%;
}

#left-panels {
    width: 40%;
}

/* Default heights for left panels */
#panel-1 {
    height: 1fr;
}

#panel-2 {
    height: 2fr;
}

#panel-3 {
    height: 2fr;
}

#panel-4 {
    height: 1fr;
}

/* Focused panel takes 50% height */
#panel-1.focused {
    height: 50%;
}

#panel-2.focused {
    height: 50%;
}

#panel-3.focused {
    height: 50%;
}

#panel-4.focused {
    height: 50%;
}

/* Compressed panels share remaining space equally */
#panel-1.compressed,
#panel-2.compressed,
#panel-3.compressed,
#panel-4.compressed {
    height: 1fr;
}
"""

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Horizontal(id="main"):
            with Vertical(id="left-panels"):
                # Use TablePanel for panels 1-3 (table display)
                yield TablePanel(1, TABLE_TABS["panel-1"])
                yield TablePanel(2, TABLE_TABS["panel-2"])
                yield TablePanel(3, TABLE_TABS["panel-3"])
                # Use InfoPanel for panel 4 (text display)
                yield InfoPanel(4, PANEL_TABS["panel-4"])
            with Vertical(id="right-panels"):
                yield ResultsPanel(id="panel-0")
                # Panel 6 uses InfoPanel (text display)
                yield InfoPanel(5, PANEL_TABS["panel-5"])

    def action_focus_results(self) -> None:
        self._reset_left_panel_sizes()
        self.query_one("#panel-0").focus()

    def action_focus_panel_1(self) -> None:
        self.query_one("#panel-1").focus()

    def action_focus_panel_2(self) -> None:
        self.query_one("#panel-2").focus()

    def action_focus_panel_3(self) -> None:
        self.query_one("#panel-3").focus()

    def action_focus_panel_4(self) -> None:
        self.query_one("#panel-4").focus()

    def action_focus_panel_5(self) -> None:
        self._reset_left_panel_sizes()
        self.query_one("#panel-5").focus()

    def _reset_left_panel_sizes(self) -> None:
        for i in range(1, 5):
            panel = self.query_one(f"#panel-{i}")
            panel.remove_class("focused", "compressed")

    def _apply_config_styles(self) -> None:
        """Apply dynamic styles from config."""
        # Apply panel width settings
        left_width = get_config_value("left_panel_width_percent", 40)
        right_width = 100 - left_width

        try:
            left_panels = self.query_one("#left-panels")
            left_panels.styles.width = f"{left_width}%"
            right_panels = self.query_one("#right-panels")
            right_panels.styles.width = f"{right_width}%"
        except Exception:
            pass

        # Apply results panel height
        results_height = get_config_value("results_panel_height_percent", 80)
        try:
            results_panel = self.query_one("#panel-0")
            results_panel.styles.height = f"{results_height}%"
        except Exception:
            pass

        # Apply scrollbar settings to all panels
        scrollbar_v_width = get_config_value("scrollbar_vertical_width", 1)
        scrollbar_h_height = get_config_value("scrollbar_horizontal_height", 1)

        for panel_id in [
            "panel-0",
            "panel-1",
            "panel-2",
            "panel-3",
            "panel-4",
            "panel-5",
        ]:
            try:
                panel = self.query_one(f"#{panel_id}")
                panel.styles.scrollbar_size_vertical = scrollbar_v_width
                panel.styles.scrollbar_size_horizontal = scrollbar_h_height
            except Exception:
                pass

    def action_scroll_down(self) -> None:
        if self.focused:
            # If focused on DataTable, move cursor instead of scrolling
            from textual.widgets import DataTable

            if isinstance(self.focused, DataTable):
                self.focused.action_cursor_down()
            else:
                self.focused.scroll_down()

    def action_scroll_up(self) -> None:
        if self.focused:
            # If focused on DataTable, move cursor instead of scrolling
            from textual.widgets import DataTable

            if isinstance(self.focused, DataTable):
                self.focused.action_cursor_up()
            else:
                self.focused.scroll_up()

    def action_scroll_left(self) -> None:
        if self.focused:
            # For DataTable with row cursor, left/right should scroll the view
            # not move cursor (since we're selecting whole rows)
            self.focused.scroll_left()

    def action_scroll_right(self) -> None:
        if self.focused:
            # For DataTable with row cursor, left/right should scroll the view
            # not move cursor (since we're selecting whole rows)
            self.focused.scroll_right()

    def action_scroll_home_trigger(self) -> None:
        current_time = time.time()
        if current_time - self._last_g_time < 0.5:
            # Double tap detected
            if self.focused:
                self.focused.scroll_home()
        self._last_g_time = current_time

    def action_scroll_end(self) -> None:
        if self.focused:
            self.focused.scroll_end()

    def action_next_tab(self) -> None:
        if not self.focused or not isinstance(self.focused, (InfoPanel, TablePanel)):
            return

        if self.focused.next_tab():
            # Load content for new tab (lazy loading)
            self._load_current_tab_lazy()

    def action_prev_tab(self) -> None:
        if not self.focused or not isinstance(self.focused, (InfoPanel, TablePanel)):
            return

        if self.focused.prev_tab():
            # Load content for new tab (lazy loading)
            self._load_current_tab_lazy()

    def _load_current_tab_lazy(self) -> None:
        """Load the current tab's data lazily (only if not already loaded)."""
        if not self.focused:
            return

        panel = self.focused
        panel_id = panel.id or ""

        if isinstance(panel, InfoPanel):
            cmd_func, args, formatter = panel.get_current_tab_command()
            # Get current tab name from panel's private attributes
            tab_name = (
                panel._tabs[panel._current_tab_index][0]
                if panel._tabs and panel._current_tab_index < len(panel._tabs)
                else ""
            )

            # Check if already loaded
            if (panel_id, tab_name) in self._loaded_tabs:
                return  # Already loaded, no need to refresh

            # Load lazily
            task = asyncio.create_task(
                self._refresh_text_panel_lazy(panel_id, tab_name, cmd_func, args, formatter)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        elif isinstance(panel, TablePanel):
            cmd_func, args, formatter, parser = panel.get_current_tab_command()
            # Get current tab name from panel's private attributes
            tab_name = (
                panel._tabs[panel._current_tab_index][0]
                if panel._tabs and panel._current_tab_index < len(panel._tabs)
                else ""
            )

            # Check if already loaded
            if (panel_id, tab_name) in self._loaded_tabs:
                return  # Already loaded, no need to refresh

            # Load lazily
            task = asyncio.create_task(
                self._refresh_table_panel_lazy(
                    panel_id, tab_name, cmd_func, args, formatter, parser
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        elif isinstance(panel, TablePanel):
            cmd_func, args, formatter, parser = panel.get_current_tab_command()
            # Get current tab name from panel's private attributes
            tab_name = (
                panel._tabs[panel._current_tab_index][0]
                if panel._tabs and panel._current_tab_index < len(panel._tabs)
                else ""
            )

            # Check if already loaded
            if (panel_id, tab_name) in self._loaded_tabs:
                return  # Already loaded, no need to refresh

            # Load lazily
            task = asyncio.create_task(
                self._refresh_table_panel_lazy(
                    panel_id, tab_name, cmd_func, args, formatter, parser
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def _refresh_current_panel(self) -> None:
        """Refresh the currently focused panel."""
        if not self.focused:
            return

        panel = self.focused
        panel_id = panel.id or ""

        if isinstance(panel, InfoPanel):
            cmd_func, args, formatter = panel.get_current_tab_command()
            task = asyncio.create_task(
                self._refresh_text_panel(panel_id, cmd_func, args, formatter)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        elif isinstance(panel, TablePanel):
            cmd_func, args, formatter, parser = panel.get_current_tab_command()
            task = asyncio.create_task(
                self._refresh_table_panel(panel_id, cmd_func, args, formatter, parser)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def action_refresh(self) -> None:
        if not self.focused:
            return

        if isinstance(self.focused, (InfoPanel, TablePanel)):
            self._refresh_current_panel()

    async def action_quit(self) -> None:
        """Override quit action to ensure proper cleanup."""
        # Stop auto-refresh first
        await self._stop_auto_refresh()

        # Cancel all background tasks before quitting
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete/cancel
        if self._background_tasks:
            await asyncio.gather(*list(self._background_tasks), return_exceptions=True)

        self._background_tasks.clear()

        # Call parent's quit action
        await super().action_quit()

    def action_help(self) -> None:
        from verdideck.ui import HelpModal

        self.push_screen(HelpModal())

    def on_info_panel_focused(self, message: InfoPanel.Focused) -> None:
        # Remove all focus/compressed classes from panels 1-4
        for i in range(1, 5):
            panel = self.query_one(f"#panel-{i}")
            panel.remove_class("focused", "compressed")

        # Add focused class to the focused panel
        focused_panel = self.query_one(f"#{message.panel_id}")
        focused_panel.add_class("focused")

        # Add compressed class to other panels
        for i in range(1, 5):
            if f"panel-{i}" != message.panel_id:
                panel = self.query_one(f"#panel-{i}")
                panel.add_class("compressed")

    def on_table_panel_focused(self, message: TablePanel.Focused) -> None:
        # Remove all focus/compressed classes from panels 1-4
        for i in range(1, 5):
            panel = self.query_one(f"#panel-{i}")
            panel.remove_class("focused", "compressed")

        # Add focused class to the focused panel
        focused_panel = self.query_one(f"#{message.panel_id}")
        focused_panel.add_class("focused")

        # Add compressed class to other panels
        for i in range(1, 5):
            if f"panel-{i}" != message.panel_id:
                panel = self.query_one(f"#panel-{i}")
                panel.add_class("compressed")

    async def on_mount(self) -> None:
        # Apply dynamic styles from config
        self._apply_config_styles()

        # Set initial focus based on config
        initial_panel = get_config_value("initial_focus_panel", 0)

        def set_initial_focus() -> None:
            if initial_panel == 0 or initial_panel == 5:
                self._reset_left_panel_sizes()
            try:
                self.query_one(f"#panel-{initial_panel}").focus()
            except Exception:
                # Fallback to panel-0 if config value is invalid
                self._reset_left_panel_sizes()
                self.query_one("#panel-0").focus()

        self.call_after_refresh(set_initial_focus)

        # BATCH LOAD all startup data in a single operation
        # This avoids session conflicts and improves startup time
        async def batch_load_startup() -> None:
            # Load all data in a separate thread (single session)
            self._startup_data_cache = await asyncio.to_thread(load_all_startup_data)

            # Populate panels with cached data
            for panel_id in ["panel-1", "panel-2", "panel-3", "panel-4", "panel-5"]:
                if panel_id not in self._startup_data_cache:
                    continue

                panel_data = self._startup_data_cache[panel_id]

                # Get the first (default) tab for this panel
                for tab_name, tab_data in panel_data.items():
                    try:
                        if panel_id in ["panel-1", "panel-2", "panel-3"]:
                            table_panel = self.query_one(f"#{panel_id}", TablePanel)
                            # Get parser and formatter for this tab
                            (
                                cmd_func,
                                args,
                                formatter,
                                parser,
                            ) = table_panel.get_current_tab_command()

                            # Apply formatter if provided
                            stdout_output = (
                                tab_data["stdout"].strip()
                                if tab_data["stdout"].strip()
                                else "No output"
                            )
                            if formatter is not None and callable(formatter):
                                stdout_output = str(formatter(stdout_output))

                            # Parse to table data
                            table_data: dict[str, Any] = (
                                parser(stdout_output)  # type: ignore[misc]
                                if callable(parser)
                                else {"headers": [], "rows": [], "footer": stdout_output}
                            )

                            # Update panel
                            table_panel.update_content(table_data)

                            # Handle stderr if present
                            if tab_data["stderr"].strip():
                                stderr = tab_data["stderr"].strip()
                                if not (
                                    "configuration file" in stderr.lower()
                                    and "does not exist" in stderr.lower()
                                ):
                                    cmd_name = getattr(cmd_func, "name", str(cmd_func))
                                    error_msg = format_error_message(cmd_name, stderr)
                                    try:
                                        results_panel = self.query_one("#panel-0", ResultsPanel)
                                        results_panel.write(error_msg)
                                    except Exception:
                                        pass

                        elif panel_id in ["panel-4", "panel-5"]:
                            info_panel = self.query_one(f"#{panel_id}", InfoPanel)
                            # Get formatter for this tab
                            cmd_func, args, formatter = info_panel.get_current_tab_command()

                            # Apply formatter if provided
                            stdout_output = (
                                tab_data["stdout"].strip()
                                if tab_data["stdout"].strip()
                                else "No output"
                            )
                            if formatter is not None and callable(formatter):
                                stdout_output = str(formatter(stdout_output))

                            # Update panel
                            info_panel.update_content(stdout_output)

                            # Handle stderr if present
                            if tab_data["stderr"].strip():
                                stderr = tab_data["stderr"].strip()
                                if not (
                                    "configuration file" in stderr.lower()
                                    and "does not exist" in stderr.lower()
                                ):
                                    cmd_name = getattr(cmd_func, "name", str(cmd_func))
                                    error_msg = format_error_message(cmd_name, stderr)
                                    try:
                                        results_panel = self.query_one("#panel-0", ResultsPanel)
                                        results_panel.write(error_msg)
                                    except Exception:
                                        pass

                        # Mark this tab as loaded
                        self._loaded_tabs.add((panel_id, tab_name))

                    except Exception:
                        pass

        # Start batch loading in background
        task = asyncio.create_task(batch_load_startup())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        # Start auto-refresh if enabled
        await self._start_auto_refresh()

    async def _start_auto_refresh(self) -> None:
        """Start the auto-refresh background task."""
        interval = get_config_value("auto_refresh_interval", 10)
        if interval > 0 and self._auto_refresh_enabled:
            self._auto_refresh_task = asyncio.create_task(self._auto_refresh_loop())
            self._background_tasks.add(self._auto_refresh_task)
            self._auto_refresh_task.add_done_callback(self._background_tasks.discard)
        elif interval <= 0:
            # Disable auto-refresh if interval is 0 or negative
            self._auto_refresh_enabled = False

    async def _stop_auto_refresh(self) -> None:
        """Stop the auto-refresh background task."""
        if self._auto_refresh_task and not self._auto_refresh_task.done():
            self._auto_refresh_task.cancel()
            try:
                await self._auto_refresh_task
            except asyncio.CancelledError:
                pass
            self._auto_refresh_task = None

    async def _auto_refresh_loop(self) -> None:
        """Background task that periodically refreshes all panels.

        Executes panel refreshes sequentially to avoid SQLAlchemy session conflicts.
        Focused panel is refreshed first for better responsiveness.
        """
        try:
            while True:
                interval = get_config_value("auto_refresh_interval", 10)
                # Stop if interval is 0 or negative
                if interval <= 0:
                    self._auto_refresh_enabled = False
                    break

                await asyncio.sleep(interval)

                # Get currently focused panel to refresh it first
                focused_panel_id = None
                if self.focused:
                    focused_panel_id = getattr(self.focused, "id", None)

                all_panels = ["panel-1", "panel-2", "panel-3", "panel-4", "panel-5"]

                # Reorder: focused panel first
                if focused_panel_id and focused_panel_id in all_panels:
                    all_panels.remove(focused_panel_id)
                    all_panels.insert(0, focused_panel_id)

                # Refresh panels SEQUENTIALLY to avoid session conflicts
                for panel_id in all_panels:
                    try:
                        if panel_id in ["panel-1", "panel-2", "panel-3"]:
                            table_panel = self.query_one(f"#{panel_id}", TablePanel)
                            (
                                cmd_func,
                                args,
                                formatter,
                                parser,
                            ) = table_panel.get_current_tab_command()
                            await self._refresh_table_panel(
                                panel_id, cmd_func, args, formatter, parser
                            )
                        elif panel_id in ["panel-4", "panel-5"]:
                            info_panel = self.query_one(f"#{panel_id}", InfoPanel)
                            cmd_func, args, formatter = info_panel.get_current_tab_command()
                            await self._refresh_text_panel(panel_id, cmd_func, args, formatter)
                    except Exception:
                        continue
        except asyncio.CancelledError:
            # Task was cancelled - this is expected
            pass

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self._auto_refresh_enabled = not self._auto_refresh_enabled

        if self._auto_refresh_enabled:
            # Start auto-refresh
            task = asyncio.create_task(self._start_auto_refresh())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            # Show notification in results panel
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                interval = get_config_value("auto_refresh_interval", 10)
                results_panel.write(f"Auto-refresh enabled (interval: {interval}s)")
            except Exception:
                pass
        else:
            # Stop auto-refresh
            task = asyncio.create_task(self._stop_auto_refresh())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            # Show notification in results panel
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                results_panel.write("Auto-refresh disabled")
            except Exception:
                pass

    async def on_unmount(self) -> None:
        """Clean up resources when app is unmounting."""
        # Stop auto-refresh first
        await self._stop_auto_refresh()

        # Cancel all background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to be cancelled
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()

    async def _refresh_text_panel(
        self,
        panel_id: str,
        command_func: object,
        args: list[str],
        formatter: Optional[object] = None,
    ) -> None:
        """Refresh text panel (InfoPanel) content by running command.

        Args:
            panel_id: ID of the panel to refresh
            command_func: Command function to execute
            args: Command arguments
            formatter: Optional text formatter

        Note:
            - stdout is processed and displayed in the target panel
            - stderr is always written to panel-0 (ResultsPanel)
        """
        try:
            result = await self._runner.run_command(command_func, args)  # type: ignore[arg-type]

            # Process stdout for target panel
            stdout_output: str = result.stdout.strip() if result.stdout.strip() else "No output"

            # Apply formatter if provided
            if formatter is not None and callable(formatter):
                stdout_output = str(formatter(stdout_output))

            # Process stderr - always write to panel-0
            if result.stderr.strip():
                stderr = result.stderr.strip()
                # Skip "configuration file does not exist" warnings
                if not (
                    "configuration file" in stderr.lower() and "does not exist" in stderr.lower()
                ):
                    cmd_name = getattr(command_func, "name", str(command_func))
                    error_msg = format_error_message(cmd_name, stderr)
                    try:
                        results_panel = self.query_one("#panel-0", ResultsPanel)
                        # Combine panel info and error into single message for better deduplication
                        results_panel.write(error_msg)
                    except Exception:
                        pass

            # Update target panel content
            info_panel = self.query_one(f"#{panel_id}", InfoPanel)
            info_panel.update_content(stdout_output)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_message = f"Error: {str(e)}"
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                # Only write unique error messages
                results_panel.write(error_message)
            except Exception:
                pass

            try:
                info_panel = self.query_one(f"#{panel_id}", InfoPanel)
                info_panel.update_content(error_message)
            except Exception:
                pass

    async def _refresh_table_panel(
        self,
        panel_id: str,
        command_func: object,
        args: list[str],
        formatter: Optional[object],
        parser: object,
    ) -> None:
        """Refresh table panel (TablePanel) content by running command.

        Args:
            panel_id: ID of the panel to refresh
            command_func: Command function to execute
            args: Command arguments
            formatter: Optional text formatter
            parser: Parser to convert text to table data

        Note:
            - stdout is processed, parsed, and displayed in the target panel
            - stderr is always written to panel-0 (ResultsPanel)
        """
        try:
            result = await self._runner.run_command(command_func, args)  # type: ignore[arg-type]

            # Process stdout
            stdout_output: str = result.stdout.strip() if result.stdout.strip() else "No output"

            # Apply formatter if provided
            if formatter is not None and callable(formatter):
                stdout_output = str(formatter(stdout_output))

            # Parse to table data
            table_data: dict[str, Any] = (
                parser(stdout_output)  # type: ignore[misc]
                if callable(parser)
                else {"headers": [], "rows": [], "footer": stdout_output}
            )

            # Process stderr
            if result.stderr.strip():
                stderr = result.stderr.strip()
                if not (
                    "configuration file" in stderr.lower() and "does not exist" in stderr.lower()
                ):
                    cmd_name = getattr(command_func, "name", str(command_func))
                    error_msg = format_error_message(cmd_name, stderr)
                    try:
                        results_panel = self.query_one("#panel-0", ResultsPanel)
                        # Combine panel info and error into single message for better deduplication
                        results_panel.write(error_msg)
                    except Exception:
                        pass

            # Update target panel
            table_panel = self.query_one(f"#{panel_id}", TablePanel)
            table_panel.update_content(table_data)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_message = f"Error: {str(e)}"
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                # Only write unique error messages
                results_panel.write(error_message)
            except Exception:
                pass

            try:
                table_panel = self.query_one(f"#{panel_id}", TablePanel)
                # Show error in footer
                table_panel.update_content({"headers": [], "rows": [], "footer": error_message})
            except Exception:
                pass

    async def _refresh_text_panel_lazy(
        self,
        panel_id: str,
        tab_name: str,
        command_func: object,
        args: list[str],
        formatter: Optional[object] = None,
    ) -> None:
        """Lazy load text panel tab content using batch loader.

        Args:
            panel_id: ID of the panel to refresh
            tab_name: Tab name being loaded
            command_func: Command function to execute
            args: Command arguments
            formatter: Optional text formatter
        """
        try:
            from verdideck.core.batch_loader import load_tab_data

            # Load data using batch loader (single session)
            tab_data = await asyncio.to_thread(
                load_tab_data, panel_id, tab_name, command_func, args
            )

            # Apply formatter if provided
            stdout_output = (
                tab_data["stdout"].strip() if tab_data["stdout"].strip() else "No output"
            )
            if formatter is not None and callable(formatter):
                stdout_output = str(formatter(stdout_output))

            # Update panel
            info_panel = self.query_one(f"#{panel_id}", InfoPanel)
            info_panel.update_content(stdout_output)

            # Handle stderr
            if tab_data["stderr"].strip():
                stderr = tab_data["stderr"].strip()
                if not (
                    "configuration file" in stderr.lower() and "does not exist" in stderr.lower()
                ):
                    cmd_name = getattr(command_func, "name", str(command_func))
                    error_msg = format_error_message(cmd_name, stderr)
                    try:
                        results_panel = self.query_one("#panel-0", ResultsPanel)
                        results_panel.write(error_msg)
                    except Exception:
                        pass

            # Mark as loaded
            self._loaded_tabs.add((panel_id, tab_name))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_message = f"Error: {str(e)}"
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                results_panel.write(error_message)
            except Exception:
                pass

            try:
                info_panel = self.query_one(f"#{panel_id}", InfoPanel)
                info_panel.update_content(error_message)
            except Exception:
                pass

    async def _refresh_table_panel_lazy(
        self,
        panel_id: str,
        tab_name: str,
        command_func: object,
        args: list[str],
        formatter: Optional[object],
        parser: object,
    ) -> None:
        """Lazy load table panel tab content using batch loader.

        Args:
            panel_id: ID of the panel to refresh
            tab_name: Tab name being loaded
            command_func: Command function to execute
            args: Command arguments
            formatter: Optional text formatter
            parser: Parser to convert text to table data
        """
        try:
            from verdideck.core.batch_loader import load_tab_data

            # Load data using batch loader (single session)
            tab_data = await asyncio.to_thread(
                load_tab_data, panel_id, tab_name, command_func, args
            )

            # Apply formatter if provided
            stdout_output = (
                tab_data["stdout"].strip() if tab_data["stdout"].strip() else "No output"
            )
            if formatter is not None and callable(formatter):
                stdout_output = str(formatter(stdout_output))

            # Parse to table data
            table_data: dict[str, Any] = (
                parser(stdout_output)  # type: ignore[misc]
                if callable(parser)
                else {"headers": [], "rows": [], "footer": stdout_output}
            )

            # Update panel
            table_panel = self.query_one(f"#{panel_id}", TablePanel)
            table_panel.update_content(table_data)

            # Handle stderr
            if tab_data["stderr"].strip():
                stderr = tab_data["stderr"].strip()
                if not (
                    "configuration file" in stderr.lower() and "does not exist" in stderr.lower()
                ):
                    cmd_name = getattr(command_func, "name", str(command_func))
                    error_msg = format_error_message(cmd_name, stderr)
                    try:
                        results_panel = self.query_one("#panel-0", ResultsPanel)
                        results_panel.write(error_msg)
                    except Exception:
                        pass

            # Mark as loaded
            self._loaded_tabs.add((panel_id, tab_name))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_message = f"Error: {str(e)}"
            try:
                results_panel = self.query_one("#panel-0", ResultsPanel)
                results_panel.write(error_message)
            except Exception:
                pass

            try:
                table_panel = self.query_one(f"#{panel_id}", TablePanel)
                table_panel.update_content({"headers": [], "rows": [], "footer": error_message})
            except Exception:
                pass


def main() -> None:
    app = VerdiDeckApp()
    app.run()


if __name__ == "__main__":
    main()
