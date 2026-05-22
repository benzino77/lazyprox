from textual.binding import Binding

from lazyprox.data import ProxmoxData
from lazyprox.widgets import BaseDataTableWidget


class LxcWidget(BaseDataTableWidget):
    nodes_columns: tuple = (
        {"name": "Name", "sort_key": "N",
            "sort_description": "Sort by name", "sort_action": "sort('Name')", "sort_key_show": False, "type": "string"},
        {"name": "Vmid", "sort_key": "V",
            "sort_description": "Sort by vmid", "sort_action": "sort('Vmid')", "sort_key_show": False, "type": "integer"},
        {"name": "Status", "sort_key": "S",
            "sort_description": "Sort by status", "sort_action": "sort('Status')", "sort_key_show": False, "type": "string"},
        {"name": "Memory", "sort_key": "M",
            "sort_description": "Sort by memory", "sort_action": "sort('Memory')", "sort_key_show": False, "type": "percent"},
        {"name": "CPU", "sort_key": "C",
            "sort_description": "Sort by CPU", "sort_action": "sort('CPU')", "sort_key_show": False, "type": "percent"},
        # {"name": "Tags", "sort_key": "T",
        #     "sort_description": "Sort by tags", "sort_action": "sort('Tags')", "sort_key_show": False, "type": "string"},
        {"name": "Node", "sort_key": "O",
            "sort_description": "Sort by node", "sort_action": "sort('Node')", "sort_key_show": False, "type": "string"},
    )
    BINDINGS = [*[Binding(key=column["sort_key"], action=column["sort_action"], description=column["sort_description"], show=column["sort_key_show"]) for column in nodes_columns],
                Binding(key="ctrl+s", action="sort_order()",
                        description="Sorting order", show=False),
                Binding(key="d", action="change_view()",
                        description="Change display", show=True),
                ]

    sort_by_column = nodes_columns[0]["name"]  # default sort by first column
    table_type = "lxc"
    table_border_title = "LXC containers"
    row_index_position = 0
    details_mode = ["summary", "graphs"]
    details_widget = "DetailsWidget"

    def build_row(self):
        lxcs = ProxmoxData.get_guests_list("lxc")
        for lxc in lxcs:
            if not lxc.get("status/current"):
                continue
            yield (lxc["name"], str(lxc["vmid"]), lxc["status"],
                   f"{(lxc['status/current']['mem']/lxc['status/current']['maxmem'])*100:.1f}%", f"{lxc['status/current']['cpu']*100:.1f}%", lxc["node"])
