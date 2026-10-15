"""Command navigation panel for the left sidebar."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


class CommandPanel(VerticalScroll):
    """Left sidebar showing command categories."""

    DEFAULT_CSS = """
    CommandPanel {
        width: 20%;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("[1] computer / code / plugin", classes="command-category")
        yield Static("[2] process / calcjob", classes="command-category")
        yield Static("[3] group / node / restapi", classes="command-category")
        yield Static("[4] config / profile", classes="command-category")
        yield Static("[5] presto / quicksetup", classes="command-category")
