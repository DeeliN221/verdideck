"""Modal screens for dialogs and help."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpModal(ModalScreen[None]):
    """Help modal showing keyboard shortcuts."""

    BINDINGS = [
        ("escape", "close_help", "Close"),
        ("?", "close_help", "Close"),
    ]

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }

    HelpModal > Container {
        width: 60;
        height: auto;
        background: $surface;
        border: $primary;
        padding: 1 2;
    }

    HelpModal .help-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    HelpModal .help-section {
        margin-top: 1;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose help modal content."""
        with Container():
            yield Label("VerdiDeck Keyboard Shortcuts", classes="help-title")

            yield Static("[bold]Navigation[/bold]", classes="help-section")
            yield Static("  j/k       : Scroll down/up")
            yield Static("  h/l       : Scroll left/right")
            yield Static("  gg        : Jump to top (press g twice)")
            yield Static("  G         : Jump to bottom")
            yield Static("  0-6       : Focus panel 0-6")

            yield Static("[bold]Tabs[/bold]", classes="help-section")
            yield Static("  [         : Previous tab")
            yield Static("  ]         : Next tab")

            yield Static("[bold]Actions[/bold]", classes="help-section")
            yield Static("  r         : Refresh current panel")

            yield Static("[bold]General[/bold]", classes="help-section")
            yield Static("  ?         : Toggle this help")
            yield Static("  q         : Quit application")
            yield Static("  Esc       : Close modal/go back")

    def action_close_help(self) -> None:
        """Close the help modal."""
        self.dismiss()


class ConfirmDialog(ModalScreen[bool]):
    """Confirmation dialog for destructive actions."""

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Vertical {
        width: 50;
        height: auto;
        background: $surface;
        border: $warning;
        padding: 1 2;
    }

    ConfirmDialog .dialog-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    ConfirmDialog .dialog-message {
        text-align: center;
        margin-bottom: 1;
    }

    ConfirmDialog .button-container {
        layout: horizontal;
        height: 3;
        align: center middle;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        """Initialize confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
        """
        super().__init__()
        self.title_text = title
        self.message_text = message

    def compose(self) -> ComposeResult:
        """Compose confirmation dialog."""
        with Vertical():
            yield Label(self.title_text, classes="dialog-title")
            yield Static(self.message_text, classes="dialog-message")
            with Container(classes="button-container"):
                yield Button("Yes (y)", variant="error", id="yes")
                yield Button("No (n)", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm action."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss(False)
