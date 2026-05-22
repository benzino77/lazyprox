from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Label, ProgressBar


class BaseSummaryView(HorizontalGroup):
    """Base class for summary views, providing a method to clear data from all Label and ProgressBar widgets."""

    def clear_data(self, reset_labels: dict[str, str] = None) -> None:
        """Function to clear data from all Label and ProgressBar widgets in the view. Optionally reset specific labels to default text.
        Args:
            reset_labels: A dictionary mapping LeftColumn widgets in details view to their default text. Defaults to None. Example: reset_labels={"#qemu_cpu_label": "CPUs:", "#qemu_memory_label": "Memory:"}
        Returns:
            None
        """
        rvg = self.query_one(".details_right", VerticalGroup)
        for c in rvg.children:
            if isinstance(c, Label):
                c.update("")
            elif isinstance(c, ProgressBar):
                c.update(progress=0)

        if reset_labels:
            for selector, text in reset_labels.items():
                self.query_one(selector, Label).update(text)
