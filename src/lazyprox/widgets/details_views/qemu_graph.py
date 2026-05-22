from datetime import datetime, timezone

from textual.containers import HorizontalGroup
from textual.app import ComposeResult

from lazyprox.data import ProxmoxData
from lazyprox.widgets.details_views import BaseGraphView, GraphWidget


class QemuGraphWidget(BaseGraphView):
    def compose(self) -> ComposeResult:
        with HorizontalGroup(classes="graphs_row"):
            yield GraphWidget(
                graph_title="Cpu usage",
                data_x_label="Time",
                data_y_label="%",
                series_1_label="CPU",
                series_2_label="",
                id="qemu_cpu_graph"
            )
            yield GraphWidget(
                graph_title="Memory usage",
                data_x_label="Time",
                data_y_label="MiB",
                series_1_label="Mem",
                series_2_label="",
                id="qemu_memory_graph")

        with HorizontalGroup(classes="graphs_row"):
            yield GraphWidget(
                graph_title="Network traffic",
                data_x_label="Time",
                data_y_label="",
                series_1_label="NetIN",
                series_2_label="NetOUT",
                id="qemu_network_graph")

            yield GraphWidget(
                graph_title="Disk IO",
                data_x_label="Time",
                data_y_label="",
                series_1_label="Read",
                series_2_label="Write",
                id="qemu_disk_graph")

    def update_data(self,  data: list[str] | None) -> None:
        if not data:
            self.clear_data()
            return

        # node = ProxmoxData.get_qemu_information(
        #     node_name=data[-1], qemu_id=int(data[1]))
        node = ProxmoxData.get_guest_information(
            node_name=data[-1], type="qemu", vmid=data[1])
        rrddata = node.get("rrddata", [])
        if not rrddata:
            return

        memused_data, cpuused_data, netin_data, netout_data, diskread_data, diskwrite_data, time_data = [
        ], [], [], [], [], [], []
        maxmem = 0
        for entry in rrddata:
            if all(key in entry for key in ["mem", "maxmem", "cpu", "time", "netin", "netout", "diskwrite", "diskread"]):
                memused_data.append(round(entry["mem"]/1024/1024))
                maxmem = entry["maxmem"]
                cpuused_data.append(entry["cpu"] * 100)
                netin_data.append(entry["netin"])
                netout_data.append(entry["netout"])
                diskread_data.append(entry["diskread"])
                diskwrite_data.append(entry["diskwrite"])
                time_data.append(datetime.fromtimestamp(
                    entry["time"], tz=timezone.utc).strftime("%d/%m/%Y %H:%M:%S %Z"))

        qemu_cpu_graph = self.query_one("#qemu_cpu_graph", GraphWidget)
        qemu_memory_graph = self.query_one("#qemu_memory_graph", GraphWidget)
        qemu_network_graph = self.query_one("#qemu_network_graph", GraphWidget)
        qemu_disk_graph = self.query_one("#qemu_disk_graph", GraphWidget)

        # we do not have any data to display on graphs
        if not time_data:
            qemu_cpu_graph.clear_data()
            qemu_memory_graph.clear_data()
            qemu_network_graph.clear_data()
            qemu_disk_graph.clear_data()
            return

        max_cpu = max(cpuused_data) or 1
        net_data = netin_data + netout_data
        max_net = max(net_data) or 1
        disk_data = diskread_data + diskwrite_data
        max_disk = max(disk_data) or 1

        qemu_cpu_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=cpuused_data,  series_y1_limit=max_cpu)

        qemu_memory_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1],
            series_y1=memused_data, series_y1_limit=maxmem/1024/1024)

        qemu_network_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1], series_y1=netin_data, series_y1_limit=max_net, series_x2=time_data, series_x2_limit=time_data[-1],
            series_y2=netout_data, series_y2_limit=max_net)

        qemu_disk_graph.set_data(
            series_x1=time_data, series_x1_limit=time_data[-1], series_y1=diskread_data, series_y1_limit=max_disk, series_x2=time_data, series_x2_limit=time_data[-1],
            series_y2=diskwrite_data, series_y2_limit=max_disk)
