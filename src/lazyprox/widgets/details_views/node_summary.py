from textual.containers import VerticalGroup
from textual.widgets import Label, ProgressBar
from textual.app import ComposeResult

from lazyprox.data import ProxmoxData
from lazyprox.common import calculate_uptime, format_bytes
from lazyprox.widgets.details_views import BaseSummaryView


class NodeSummaryWidget(BaseSummaryView):

    def compose(self) -> ComposeResult:
        with VerticalGroup(classes="details_left"):
            yield Label("Uptime:")
            yield Label("Status:")
            yield Label(f"CPUs:", id="node_cpu_label")
            yield Label("Load average:")
            yield Label(f"Memory:", id="node_memory_label")
            yield Label("HD Space:")
            yield Label("IO delay:")
            yield Label("KSM sharing:")
            yield Label("SWAP usage:")
            yield Label("CPU(s) model:")
            yield Label("CPU(s) sockets:")
            yield Label("CPU(s) cores:")
            yield Label("Kernel version:")
            yield Label("Boot mode:")
            yield Label("Manager version:")
        with VerticalGroup(classes="details_right"):
            yield Label("", id="node_uptime_value")
            yield Label("", id="node_status_value")
            yield ProgressBar(show_eta=False, total=100, id="node_cpu_bar")
            yield Label("", id="node_load_average_value")
            yield ProgressBar(show_eta=False, total=100, id="node_memory_bar")
            yield ProgressBar(show_eta=False, total=100, id="node_hd_bar")
            yield Label("", id="node_io_delay_value")
            yield Label("", id="node_ksm_sharing_value")
            yield Label("", id="node_swap_value")
            yield Label("", id="node_cpu_model_value")
            yield Label("", id="node_cpu_sockets_value")
            yield Label("", id="node_cpu_cores_value")
            yield Label("", id="node_kernel_version_value")
            yield Label("", id="node_boot_mode_value")
            yield Label("", id="node_manager_version_value")

    def update_data(self, data: list[str] | None) -> None:
        if not data:
            self.clear_data({
                "#node_cpu_label": "CPUs:",
                "#node_memory_label": "Memory:",
            })
            return

        node = ProxmoxData.get_node_information(node_name=data[0])
        uptime_str = calculate_uptime(node.get("uptime", 0))
        cpu_count = node.get('maxcpu', 0)
        status_str = data[1]
        cpu_usage = node.get("cpu", 0.0) * 100
        memory_usage = (node.get("mem", 0) / node.get("maxmem", 1)) * 100
        memory_info = f"({node.get('mem', 0)/1024/1024/1024:0.2f}GiB of {node.get('maxmem', 1)/1024/1024/1024:0.2f}GiB)"
        load_average_str = f"{', '.join(str(x) for x in node.get('full_status', {}).get('loadavg', [0, 0, 0]))}"
        hd_usage = (node.get("disk", 0) / node.get("maxdisk", 1)) * 100
        io_delay_str = f"{node.get('full_status', {}).get('wait', 0)*100:0.2f}%"

        ksm_sharing = node.get('full_status', {}).get(
            'ksm', {}).get('shared', 0)
        ksm_sharing_str = format_bytes(ksm_sharing)

        swap_total = format_bytes(node.get("full_status", {}).get(
            "swap", {}).get("total", 0))
        swap_free = format_bytes(node.get("full_status", {}).get(
            "swap", {}).get("free", 0))
        swap_used = format_bytes(node.get("full_status", {}).get(
            "swap", {}).get("used", 0))
        swap_str = f"Total: {swap_total}, Free: {swap_free}, Used: {swap_used}"
        cpu_model = node.get("full_status", {}).get(
            "cpuinfo", {}).get("model", "N/A")
        cpu_sockets = node.get("full_status", {}).get(
            "cpuinfo", {}).get("sockets", 0)
        cpu_cores = node.get("full_status", {}).get(
            "cpuinfo", {}).get("cores", 0)
        kernel_version_str = node.get("full_status", {}).get(
            "current-kernel", {}).get("release", "N/A")
        boot_mode_str = node.get("full_status", {}).get(
            "boot-info", {}).get("mode", "N/A")
        manager_version_str = node.get("full_status", {}).get(
            "pveversion", "N/A")

        self.query_one("#node_cpu_label", Label).update(f"CPUs({cpu_count}):")
        self.query_one("#node_memory_label", Label).update(
            f"Memory {memory_info}:")
        self.query_one("#node_uptime_value", Label).update(uptime_str)
        self.query_one("#node_status_value", Label).update(status_str)
        self.query_one("#node_cpu_bar", ProgressBar).update(progress=cpu_usage)
        self.query_one("#node_load_average_value",
                       Label).update(load_average_str)
        self.query_one("#node_memory_bar", ProgressBar).update(
            progress=memory_usage)
        self.query_one("#node_hd_bar", ProgressBar).update(progress=hd_usage)
        self.query_one("#node_io_delay_value", Label).update(io_delay_str)
        self.query_one("#node_ksm_sharing_value",
                       Label).update(ksm_sharing_str)
        self.query_one("#node_swap_value", Label).update(swap_str)
        self.query_one("#node_cpu_model_value", Label).update(cpu_model)
        self.query_one("#node_cpu_sockets_value",
                       Label).update(str(cpu_sockets))
        self.query_one("#node_cpu_cores_value", Label).update(str(cpu_cores))
        self.query_one("#node_kernel_version_value",
                       Label).update(kernel_version_str)
        self.query_one("#node_boot_mode_value", Label).update(boot_mode_str)
        self.query_one("#node_manager_version_value",
                       Label).update(manager_version_str)
