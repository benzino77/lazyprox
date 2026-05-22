from textual.binding import Binding

from lazyprox.data import ProxmoxData
from lazyprox.widgets import BaseDataTableWidget


class NodeWidget(BaseDataTableWidget):
    nodes_columns: tuple = (
        {"name": "Node", "sort_key": "N",
            "sort_description": "Sort by node", "sort_action": "sort('Node')", "sort_key_show": False, "type": "string"},
        {"name": "Status", "sort_key": "S",
            "sort_description": "Sort by status", "sort_action": "sort('Status')", "sort_key_show": False, "type": "string"},
        {"name": "Memory", "sort_key": "M",
            "sort_description": "Sort by memory", "sort_action": "sort('Memory')", "sort_key_show": False, "type": "percent"},
        {"name": "CPU", "sort_key": "C",
            "sort_description": "Sort by CPU", "sort_action": "sort('CPU')", "sort_key_show": False, "type": "percent"},

    )
    BINDINGS = [*[Binding(key=column["sort_key"], action=column["sort_action"], description=column["sort_description"], show=column["sort_key_show"]) for column in nodes_columns],
                Binding(key="ctrl+s", action="sort_order()",
                        description="Sorting order", show=False),
                Binding(key="d", action="change_view()",
                        description="Change display", show=True),
                ]

    sort_by_column = nodes_columns[0]["name"]  # default sort by first column
    table_type = "node"
    table_border_title = "Nodes"
    row_index_position = 0
    details_mode = ["summary", "graphs"]
    details_widget = "DetailsWidget"

    def build_row(self):
        nodes = ProxmoxData.p_prox_resources.get("nodes", [])
        for node in nodes:
            yield (node["node"], node["status"],
                   f"{node.get('mem', 0)/node.get('maxmem', 1)*100:.1f}%", f"{node.get('cpu', 0)*100:.1f}%")
