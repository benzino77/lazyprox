
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Select

from lazyprox.common import Config


class ServerSelectionScreen(Screen[int]):

    def compose(self) -> ComposeResult:
        yield Select(id="server_select", prompt="Select server", options=[(server['name'], idx) for idx, server in enumerate(Config.configuration.get("server"))])

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK and event.value is not Select.NULL:
            self.dismiss(event.value)

    def on_screen_resume(self):
        # clear the previous selection
        server_select = self.query_one("#server_select")
        server_select.value = Select.NULL
