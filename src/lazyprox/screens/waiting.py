from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import LoadingIndicator


class WaitingScreen(Screen):

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
