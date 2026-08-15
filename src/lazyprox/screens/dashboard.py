from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from textual.screen import Screen
from textual.widgets import Footer

from lazyprox.widgets import DetailsWidget, LxcWidget, NodeWidget, QemuWidget


class DashboardScreen(Screen):

    class LeftColumn(VerticalGroup):
        def compose(self) -> ComposeResult:
            yield NodeWidget(id="node_widget")
            yield LxcWidget(id="lxc_widget")
            yield QemuWidget(id="qemu_widget")

    class RightColumn(VerticalGroup):
        def compose(self) -> ComposeResult:
            yield DetailsWidget(id="details_widget", initial="node_summary_widget")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield HorizontalGroup(self.LeftColumn(), self.RightColumn())
        yield Footer(show_command_palette=False)
