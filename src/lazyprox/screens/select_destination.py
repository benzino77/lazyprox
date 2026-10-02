from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Select


class DestinationSelectionScreen(ModalScreen[str | None]):
    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    def __init__(self, guest: str, nodes: list[str]):
        super().__init__()
        self.guest = guest
        self.nodes = list(nodes)

    def compose(self) -> ComposeResult:
        with Vertical(id="destination_dialog"):
            yield Label(f"Migrate {self.guest} to:", id="destination_label")
            yield Select(
                [(node, node) for node in self.nodes],
                prompt="Select destination",
                id="destination_select",
                type_to_search=False,
            )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK and event.value is not Select.NULL:
            self.dismiss(str(event.value))
