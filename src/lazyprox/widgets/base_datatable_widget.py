import re
from typing import Iterable, Literal, TypedDict, Tuple, Dict

from textual.widgets import DataTable

from lazyprox.common import set_focus_border


class BaseDataTableWidget(DataTable):
    """
    This is a base class for all widgets which are used to display data in a table.
    It implements common functionality for all tables like sorting, filtering, updating data in the table.
    """
    class ColumnDict(TypedDict):
        name: str
        sort_key: str
        sort_description: str
        sort_action: str
        sort_key_show: bool
        type: str

    nodes_columns: Tuple[ColumnDict, ...] = ()

    # this stores boolean values for each column if it is sorted in ascending or descending order
    column_sort_order: Dict[str, bool] = {}
    # this is used to store the text which is used to filter the data in the table
    # this can also be a regex pattern
    filter_text: str = ""
    # current column which is used to sort the table
    sort_by_column: str = ""
    # id of the details widget which is used to display details of the selected row
    # this needs to be defined on child class
    details_widget: str = ""
    # type of the table - node, lxc, qemu
    table_type: Literal["node", "lxc", "qemu"] = ""
    # title of the border of the table
    table_border_title: str = ""
    # details panel mode, it is gonna be a rotational list of modes
    # first element is the currently displayed mode
    details_mode: list[str] = []

    # row_index_position variable is used to store the position of the column in the table
    # which holds the unique index of the row
    # the row for node looks like: ["node_name", "running", "50%", "50%"] and the node name is also an index for the row - so it is index 0
    # the row for lxc looks like: ["lxc_name", 100, "running", "50%", "50%", "node_name"] and the vmid is an index for the row - so it is index 1
    # the row for vm looks like: ["vm_name", 100, "running", "50%", "50%", "node_name"] and the vmid is an index for the row - so it is index 1
    row_index_position: int = 0

    def _call_update_details(self) -> None:
        try:
            details_widget = self.screen.query_one(self.details_widget)
        except Exception as e:
            return
        if (self.cursor_row >= 0 and len(self.rows) > 0):
            details_widget.update_details_data(
                selected_type=self.table_type, data=self.get_row_at(self.cursor_row), details_mode=self.details_mode[0])
        else:
            details_widget.update_details_data(
                selected_type=self.table_type, data=None, details_mode=self.details_mode[0])

    def build_row(self) -> Iterable:
        """
        This method must be implemented in the child class.
        Should return iterable of rows which will be displayed in the table.
        Each row is a tuple of values which will be displayed in the columns.
        """
        pass

    def rotate_details_mode(self) -> None:
        """
        Rotates the details_mode list by moving the first element to the last position.
        """
        if self.details_mode:
            self.details_mode.append(self.details_mode.pop(0))

    def remove_border_indicator(self, indicator: str) -> None:
        self.border_title = self.border_title.replace(
            f" {indicator}", "").replace(indicator, "")

    def add_border_indicator(self, indicator: str) -> None:
        self.remove_border_indicator(indicator)
        self.border_title = f"{self.table_border_title} {indicator}"

    def update_table_data(self) -> None:
        # let's filter data out based on the filter
        filtered_data = []
        for row in self.build_row():
            if re.search(self.filter_text, " ".join(row)):
                filtered_data.append(row)

        # let's store keys of the rows which should be in the table
        filtered_row_keys = [data[self.row_index_position]
                             for data in filtered_data]

        # remove existing rows from table which are not in the filtered rows
        for row in list(self.rows):
            if row.value not in filtered_row_keys:
                self.remove_row(row)

        # get current list of rows keys in a table (some of them might be filtered out in previous step)
        existing_rows_keys = [r.value for r in self.rows]
        for node in filtered_data:
            # if there is already such row in a table, update it's values
            # based on the new data
            if node[self.row_index_position] in existing_rows_keys:
                for idx, column in enumerate(self.nodes_columns):
                    self.update_cell(
                        row_key=node[self.row_index_position], column_key=column["name"], value=node[idx])
            # if the row is not in a table it needs to be added because it is not on the list already
            else:
                self.add_row(*node, key=node[self.row_index_position])

        self.sort_table_data(self.sort_by_column)

    def sort_table_data(self, column: str) -> None:
        # do we have something selected? index of selected row needs to be 0 or more
        # and there should be something on the rows list
        is_selected: bool = self.cursor_row >= 0 and len(self.rows) > 0
        has_focus: bool = self.has_class("focused")
        # let's store current highlighted selection in the table so when the list will be sorted we can
        # move to the row which was selected before sorting
        selected_row: list = []
        if (is_selected):
            selected_row = self.get_row_at(self.cursor_row)

        # get columns with percentage values, those needs to be sorted different
        percentage_columns = [
            col["name"] for col in self.nodes_columns if col["type"] == "percent"]
        # sorting columns with integer values also need to be handled differently
        integer_columns = [
            col["name"] for col in self.nodes_columns if col["type"] == "integer"]
        if column in percentage_columns:
            self.sort(column, key=lambda value: float(
                value[0: -1]), reverse=self.column_sort_order[column])
        elif column in integer_columns:
            self.sort(column, key=lambda value: int(
                value), reverse=self.column_sort_order[column])
        else:
            self.sort(column, reverse=self.column_sort_order[column])
        self.sort_by_column = column

        if is_selected and has_focus:
            # selected an index of a row which key is stored in the row_index_position element of the selected row
            selected_row_index = self.get_row_index(
                selected_row[self.row_index_position])
            self.move_cursor(row=selected_row_index, scroll=True)
        if has_focus:
            self._call_update_details()

    def on_mount(self) -> None:
        for c in self.nodes_columns:
            self.add_column(c["name"], key=c["name"])
            self.column_sort_order[c["name"]] = False
        self.border_title = self.table_border_title
        self.show_header = True
        self.cursor_type = "row"

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self.has_class("focused"):
            self._call_update_details()

    def on_focus(self, event) -> None:
        set_focus_border(self)
        self._call_update_details()

    def action_change_view(self) -> None:
        self.rotate_details_mode()
        self._call_update_details()

    def action_sort(self, key: str) -> None:
        self.sort_table_data(key)

    def action_sort_order(self) -> None:
        self.column_sort_order[self.sort_by_column] = not self.column_sort_order[self.sort_by_column]
        self.sort_table_data(self.sort_by_column)
