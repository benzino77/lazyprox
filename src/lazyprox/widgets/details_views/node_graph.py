from datetime import datetime, timezone

from textual.containers import HorizontalGroup
from textual.app import ComposeResult

from lazyprox.data import ProxmoxData
from lazyprox.widgets.details_views import BaseGraphView, GraphWidget


class NodeGraphWidget(BaseGraphView):
    def compose(self) -> ComposeResult:
        with HorizontalGroup(classes="graphs_row"):
            yield GraphWidget(
                graph_title="Cpu usage/IO delay",
                data_x_label="Time",
                data_y_label="%",
                series_1_label="CPU",
                series_2_label="IOd",
                id="node_cpu_io_graph"
            )
            yield GraphWidget(
                graph_title="Memory usage",
                data_x_label="Time",
                data_y_label="GiB",
                series_1_label="Mem",
                series_2_label="",
                id="node_memory_graph")

        with HorizontalGroup(classes="graphs_row"):
            yield GraphWidget(
                graph_title="Server load average",
                data_x_label="Time",
                data_y_label="",
                series_1_label="Load",
                series_2_label="",
                id="node_load_graph")

            yield GraphWidget(
                graph_title="Network traffic",
                data_x_label="Time",
                data_y_label="MiB",
                series_1_label="NetIN",
                series_2_label="NetOUT",
                id="node_network_graph")

    def update_data(self,  data: list[str] | None) -> None:
        if not data:
            self.clear_data()
            return

        node = ProxmoxData.get_node_information(node_name=data[0])
        rrddata = node.get("rrddata", [])
        if not rrddata:
            return

        memused_data, cpuused_data, loadaverage_data, iowait_data, netin_data, netout_data, time_data = [
        ], [], [], [], [], [], []
        mem_total = 0
        for entry in rrddata:
            if all(key in entry for key in ["memused", "memtotal", "cpu", "time", "loadavg", "iowait", "netin", "netout"]):
                memused_data.append(round(entry["memused"]/1024/1024/1024))
                mem_total = entry["memtotal"]
                cpuused_data.append(entry["cpu"] * 100)
                loadaverage_data.append(entry["loadavg"])
                iowait_data.append(entry["iowait"] * 100)
                netin_data.append(entry["netin"]/1024/1024)
                netout_data.append(entry["netout"]/1024/1024)
                # pass the string with the time zone, then when output_form (of X axis) is used,
                # it will be converted to the local time zone
                time_data.append(datetime.fromtimestamp(
                    entry["time"], tz=timezone.utc).strftime("%d/%m/%Y %H:%M:%S %Z"))

        node_cpu_io_graph = self.query_one("#node_cpu_io_graph", GraphWidget)
        node_memory_graph = self.query_one("#node_memory_graph", GraphWidget)
        node_load_graph = self.query_one("#node_load_graph", GraphWidget)
        node_network_graph = self.query_one("#node_network_graph", GraphWidget)

        # we do not have any data to display on graphs (any table can be checked here)
        if not time_data:
            self.clear_data()
            return

        cpu_io_data = cpuused_data + iowait_data
        max_cpu_io = max(cpu_io_data) or 1

        max_loadaverage = max(loadaverage_data) or 1

        net_data = netin_data + netout_data
        max_net = max(net_data) or 1

        node_cpu_io_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=cpuused_data, series_y1_limit=max_cpu_io,
            series_x2=time_data, series_x2_limit=time_data[-1],
            series_y2=iowait_data, series_y2_limit=max_cpu_io,
        )

        node_memory_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=memused_data, series_y1_limit=mem_total/1024/1024/1024)

        node_load_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=loadaverage_data, series_y1_limit=max_loadaverage)

        node_network_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=netin_data, series_y1_limit=max_net,
            series_x2=time_data, series_x2_limit=time_data[-1],
            series_y2=netout_data, series_y2_limit=max_net,
        )
