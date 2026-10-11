from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer

from lazyprox.widgets import DetailsWidget, LxcWidget, NodeWidget, QemuWidget
from lazyprox.widgets.details_views import NodeTasksWidget

TASKS_VIEW_ID = "node_tasks_widget"


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

    def focus_panes(self) -> list[Widget]:
        """Return dashboard panes in keyboard focus order.

        The node task list is included only while the details pane displays
        the Tasks view. Without it the order is Nodes, LXC, VMs.
        """
        panes: list[Widget] = [self.query_one(NodeWidget)]
        details_widget = self.query_one(DetailsWidget)
        if details_widget.current == TASKS_VIEW_ID:
            panes.append(self.query_one(NodeTasksWidget))
        panes.extend([self.query_one(LxcWidget), self.query_one(QemuWidget)])
        return panes

    def focus_next(self, selector: str | type = "*") -> Widget | None:
        if selector != "*":
            return super().focus_next(selector)
        return self._move_focus_in_cycle(1)

    def focus_previous(self, selector: str | type = "*") -> Widget | None:
        if selector != "*":
            return super().focus_previous(selector)
        return self._move_focus_in_cycle(-1)

    def _move_focus_in_cycle(self, direction: int) -> Widget | None:
        """Move focus to the next (1) or previous (-1) pane in the dashboard cycle."""
        panes = self.focus_panes()
        focused = self.focused
        if focused not in panes:
            return super().focus_next() if direction > 0 else super().focus_previous()
        target = panes[(panes.index(focused) + direction) % len(panes)]
        self.set_focus(target)
        return self.focused
