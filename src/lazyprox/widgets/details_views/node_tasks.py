from datetime import datetime

from textual.widgets import DataTable

from lazyprox.data import ProxmoxData


TASK_DESCRIPTIONS: dict[str, str] = {
    "aptupdate": "Update package database",
    "startall": "Bulk start VMs and Containers",
    "stopall": "Bulk shutdown VMs and Containers",
    "vzdump": "Backup job",
    "vncproxy": "VM/CT {id} - Console",
    "qmstart": "VM {id} - Start",
    "qmshutdown": "VM {id} - Shutdown",
    "qmreset": "VM {id} - Reset",
    "qmreboot": "VM {id} - Reboot",
    "qmsuspend": "VM {id} - Hibernate",
    "vzstart": "CT {id} - Start",
    "vzshutdown": "CT {id} - Shutdown",
    "vzstop": "CT {id} - Stop",
    "vzreboot": "CT {id} - Reboot",
}


class NodeTasksWidget(DataTable):

    # for now this widget is only for displaying cluster tasks, so it does not need to propagate "selected" event
    # it will be then implemented in the future displaying details of the selected task
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()

    def on_mount(self) -> None:
        self.add_column("Start Time")
        self.add_column("End Time")
        self.add_column("Node")
        self.add_column("Username")
        self.add_column("Description")
        self.add_column("Status")
        self.show_header = True
        self.cursor_type = "row"

    def get_current_tasks_list(self) -> list[tuple]:
        """Build list of tuples from the current DataTable rows."""
        current_list: list[tuple] = []
        column_keys = list(self.columns.keys())
        for row_key in self.rows:
            row_data: list[str] = []
            for col_key in column_keys:
                cell = self.get_cell(row_key, col_key)
                row_data.append(cell.plain if hasattr(
                    cell, "plain") else str(cell))
            current_list.append(tuple(row_data))
        return current_list

    def has_tasks_changed(self) -> bool:
        """
        Compare current DataTable data with fetched new task list and return True if different.
        It is comparing the all columns, because the status of the task could change running -> ok
        Comparing only row keys would not catch this situation
        Returns:
            bool: True if tasks have changed, False otherwise
        """
        current = self.get_current_tasks_list()
        new_list = self.build_new_tasks_list()
        new_list_no_upid = [t[:-1] for t in new_list]
        return current != new_list_no_upid

    def build_new_tasks_list(self) -> list[tuple]:
        new_list: list[tuple] = []
        tasks = ProxmoxData.get_cluster_tasks()
        tasks.sort(key=lambda t: t.get("starttime", 0), reverse=True)

        for task in tasks:
            start_str = datetime.fromtimestamp(
                task["starttime"]).strftime("%b %d %H:%M:%S")
            endtime = task.get("endtime", 0)
            end_str = datetime.fromtimestamp(endtime).strftime(
                "%b %d %H:%M:%S") if endtime else ""
            desc_template = TASK_DESCRIPTIONS.get(task["type"])
            if desc_template:
                desc = desc_template.format(
                    id=task["id"]) if "{id}" in desc_template else desc_template
            else:
                desc = f"{task['type']} {task['id']}".strip()
            new_list.append(
                tuple((start_str, end_str, task["node"], task["user"], desc, task["status"], task["upid"])))

        return new_list

    def update_data(self, data: list[str] | None) -> None:
        if not data:
            self.clear()
            return

        if not self.has_tasks_changed():
            return

        # store previous cursor position in the list so after refreshing the list we can move to the same position if it is still valid
        current_key = None
        if self.cursor_coordinate is not None:
            row_keys = list(self.rows.keys())
            if row_keys and self.cursor_coordinate.row < len(row_keys):
                current_key = row_keys[self.cursor_coordinate.row]

        self.clear()
        tasks = self.build_new_tasks_list()
        for task in tasks:
            self.add_row(*task[:-1], key=task[-1])

        if current_key is not None:
            try:
                index = self.get_row_index(current_key)
                self.move_cursor(row=index, column=0)
            except KeyError:
                pass
