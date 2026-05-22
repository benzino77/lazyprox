from textual.containers import VerticalGroup
from textual.widgets import Label, ProgressBar
from textual.app import ComposeResult

from lazyprox.data import ProxmoxData
from lazyprox.common import calculate_uptime, format_bytes
from lazyprox.widgets.details_views import BaseSummaryView


class QemuSummaryWidget(BaseSummaryView):

    def compose(self) -> ComposeResult:
        with VerticalGroup(classes="details_left"):
            yield Label("Uptime:")
            yield Label("Status:")
            yield Label("HA State:")
            yield Label("Node:")
            yield Label("Tags:")
            yield Label("CPUs:", id="qemu_cpu_label")
            yield Label("Memory:", id="qemu_memory_label")
            yield Label("Host memory usage:")
            yield Label("Disk(s) size:")
        with VerticalGroup(classes="details_right"):
            yield Label("", id="qemu_uptime_value")
            yield Label("", id="qemu_status_value")
            yield Label("", id="qemu_ha_state_value")
            yield Label("", id="qemu_node_value")
            yield Label("", id="qemu_tags_value")

            yield ProgressBar(show_eta=False, total=100, id="qemu_cpu_bar")
            yield ProgressBar(show_eta=False, total=100, id="qemu_memory_bar")
            yield Label("", id="qemu_host_memory_usage_value")
            yield Label("", id="qemu_disk_size_value")

    def update_data(self, data: list[str] | None) -> None:
        if not data:
            self.clear_data({
                "#qemu_cpu_label": "CPUs:",
                "#qemu_memory_label": "Memory:"
            })
            return

        node = ProxmoxData.get_guest_information(
            node_name=data[-1], type="qemu", vmid=data[1])
        status_current = node.get("status/current", {})

        uptime_str = calculate_uptime(status_current.get("uptime", 0))
        cpu_count_label = status_current.get('cpus', 0)
        status_str = data[2]
        cpu_usage = status_current.get("cpu", 0.0) * 100

        memory_usage = (status_current.get("mem", 0) /
                        status_current.get("maxmem", 1)) * 100
        memory_info_useed = format_bytes(status_current.get('mem', 0))
        memory_info_max = format_bytes(status_current.get('maxmem', 1))
        memory_info_label = f"({memory_info_useed} of {memory_info_max})"

        host_memory_usage = format_bytes(status_current.get('memhost', 0))

        ha_state = status_current.get("ha", {})
        managed = ha_state.get("managed", 0) == 1
        ha_state_str = "none"
        if managed:  # if managed, then we have some more information
            ha_state_str = f"{ha_state['state']}, Group: {ha_state.get('group', 'N/A')}"
        disk_size = format_bytes(status_current.get('maxdisk', 0))

        self.query_one("#qemu_cpu_label", Label).update(
            f"CPUs({cpu_count_label}):")
        self.query_one("#qemu_memory_label", Label).update(
            f"Memory {memory_info_label}:")
        self.query_one("#qemu_uptime_value", Label).update(uptime_str)
        self.query_one("#qemu_status_value", Label).update(status_str)
        self.query_one("#qemu_ha_state_value", Label).update(ha_state_str)
        self.query_one("#qemu_node_value", Label).update(
            node.get("node", "N/A"))
        self.query_one("#qemu_tags_value", Label).update(
            node.get("tags", ""))
        self.query_one("#qemu_cpu_bar", ProgressBar).update(progress=cpu_usage)
        self.query_one("#qemu_memory_bar", ProgressBar).update(
            progress=memory_usage)
        self.query_one("#qemu_host_memory_usage_value",
                       Label).update(host_memory_usage)
        self.query_one("#qemu_disk_size_value", Label).update(disk_size)
