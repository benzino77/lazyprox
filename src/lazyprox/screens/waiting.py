from textual.screen import Screen
from textual.widgets import LoadingIndicator
from textual.app import ComposeResult


class WaitingScreen(Screen):

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
