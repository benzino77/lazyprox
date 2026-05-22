from typing import Literal

from textual.app import ComposeResult
from textual.widgets import ContentSwitcher

from lazyprox.widgets.details_views import NodeSummaryWidget, NodeGraphWidget, LXCSummaryWidget, LXCGraphWidget, QemuSummaryWidget, QemuGraphWidget


class DetailsWidget(ContentSwitcher):

    def compose(self) -> ComposeResult:
        yield NodeSummaryWidget(id="node_summary_widget")
        yield NodeGraphWidget(id="node_graphs_widget")
        yield LXCSummaryWidget(id="lxc_summary_widget")
        yield LXCGraphWidget(id="lxc_graphs_widget")
        yield QemuSummaryWidget(id="qemu_summary_widget")
        yield QemuGraphWidget(id="qemu_graphs_widget")

    def update_details_data(self, selected_type: Literal["node", "lxc", "qemu"], data: list[str] | None, details_mode: str | None) -> None:
        if details_mode:
            self.parent.border_title = details_mode.replace(
                "_", " ").capitalize()

        if selected_type == "node":
            if details_mode == "summary":
                self.current = "node_summary_widget"
                self.query_one("NodeSummaryWidget").update_data(data=data)
            elif details_mode == "graphs":
                self.current = "node_graphs_widget"
                self.query_one("NodeGraphWidget").update_data(data=data)
        if selected_type == "lxc":
            if details_mode == "summary":
                self.current = "lxc_summary_widget"
                self.query_one("LXCSummaryWidget").update_data(data=data)
            elif details_mode == "graphs":
                self.current = "lxc_graphs_widget"
                self.query_one("LXCGraphWidget").update_data(data=data)
        if selected_type == "qemu":
            if details_mode == "summary":
                self.current = "qemu_summary_widget"
                self.query_one("QemuSummaryWidget").update_data(data=data)
            elif details_mode == "graphs":
                self.current = "qemu_graphs_widget"
                self.query_one("QemuGraphWidget").update_data(data=data)
