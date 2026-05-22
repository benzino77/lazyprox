from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input


class FilterScreen(ModalScreen[str]):
    BINDINGS = [("escape", "app.pop_screen", "Back to dashboard")]

    def __init__(self, widget, *args, **kwargs):
        self.widget = widget
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter by", id="input_filter", value=self.widget.filter_text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
