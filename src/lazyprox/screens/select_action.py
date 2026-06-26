from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Select


class ActionSelectionScreen(ModalScreen[str]):
    BINDINGS = [("escape", "app.pop_screen", "Back to dashboard")]

    def __init__(self, items: list[str] = []):
        super().__init__()
        self.items = items

    def compose(self) -> ComposeResult:
        options = [(item, item) for item in self.items]
        yield Select(id="action_select", prompt="Select action", options=options)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK and event.value is not Select.NULL:
            self.dismiss(event.value)

