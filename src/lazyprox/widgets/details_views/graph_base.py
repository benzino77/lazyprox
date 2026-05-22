from textual.containers import VerticalGroup


class BaseGraphView(VerticalGroup):
    """Base class for graph views, providing a method to clear data from all GraphWidgets."""

    def clear_data(self) -> None:
        for g in self.query("GraphWidget"):
            g.clear_data()
