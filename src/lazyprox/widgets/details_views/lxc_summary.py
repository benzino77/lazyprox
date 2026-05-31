from textual.containers import VerticalGroup
from textual.widgets import Label, ProgressBar
from textual.app import ComposeResult

from lazyprox.data import ProxmoxData
from lazyprox.common import calculate_uptime, format_bytes
from lazyprox.widgets.details_views import BaseSummaryView


class LXCSummaryWidget(BaseSummaryView):
    def compose(self) -> ComposeResult:
        with VerticalGroup(classes="details_left"):
            yield Label("Uptime:")
            yield Label("Status:")
            yield Label("HA State:")
            yield Label("Node:")
            yield Label("Tags:")
            yield Label("Unprivileged:")
            yield Label("CPUs:", id="lxc_cpu_label")
            yield Label("Memory:", id="lxc_memory_label")
            yield Label("SWAP:", id="lxc_swap_label")
            yield Label("Boot disk:", id="lxc_boot_disk_label")

        with VerticalGroup(classes="details_right"):
            yield Label("", id="lxc_uptime_value")
            yield Label("", id="lxc_status_value")
            yield Label("", id="lxc_ha_state_value")
            yield Label("", id="lxc_node_value")
            yield Label("", id="lxc_tags_value")
            yield Label("", id="lxc_unprivileged_value")

            yield ProgressBar(show_eta=False, total=100, id="lxc_cpu_bar")
            yield ProgressBar(show_eta=False, total=100, id="lxc_memory_bar")
            yield ProgressBar(show_eta=False, total=100, id="lxc_swap_bar")
            yield ProgressBar(show_eta=False, total=100, id="lxc_boot_disk_bar")

    def update_data(self, data: list[str] | None) -> None:
        if not data:
            self.clear_data({
                "#lxc_cpu_label": "CPUs:",
                "#lxc_memory_label": "Memory:",
                "#lxc_swap_label": "SWAP:",
                "#lxc_boot_disk_label": "Boot disk:"
            })
            return

        node = ProxmoxData.get_guest_information(
            node_name=data[-1], resource_type="lxc", vmid=data[1])
        status_current = node.get("status/current", {})

        uptime_str = calculate_uptime(node.get("uptime", 0))
        cpu_count = status_current.get('cpus', 0)
        status_str = data[2]
        cpu_usage = status_current.get("cpu", 0.0) * 100

        memory_usage = (status_current.get("mem", 0) /
                        status_current.get("maxmem", 1)) * 100
        memory_info_used = format_bytes(status_current.get('mem', 0))
        memory_info_max = format_bytes(status_current.get('maxmem', 1))
        memory_info_label = f"({memory_info_used} of {memory_info_max}) "

        ha_state = status_current.get("ha", {})
        managed = ha_state.get("managed", 0) == 1
        ha_state_str = "none"
        if managed:  # if managed, then we have some more information
            ha_state_str = f"{ha_state['state']}, Group: {ha_state.get('group', 'N/A')}"

        swap_usage = (status_current.get("swap", 0) /
                      status_current.get("maxswap", 1))*100
        swap_info_used = format_bytes(status_current.get('swap', 0))
        swap_info_max = format_bytes(status_current.get('maxswap', 1))
        swap_info_label = f"({swap_info_used} of {swap_info_max})"

        boot_disk_usage = (status_current.get("disk", 0) /
                           status_current.get("maxdisk", 1)) * 100
        boot_disk_used = format_bytes(status_current.get('disk', 0))
        boot_disk_max = format_bytes(status_current.get('maxdisk', 1))
        boot_disk_label = f"({boot_disk_used} of {boot_disk_max})"

        self.query_one("#lxc_cpu_label", Label).update(f"CPUs({cpu_count}):")
        self.query_one("#lxc_memory_label", Label).update(
            f"Memory {memory_info_label}:")
        self.query_one("#lxc_swap_label", Label).update(
            f"SWAP {swap_info_label}:")
        self.query_one("#lxc_boot_disk_label", Label).update(
            f"Boot disk {boot_disk_label}:")
        self.query_one("#lxc_uptime_value", Label).update(uptime_str)
        self.query_one("#lxc_status_value", Label).update(status_str)
        self.query_one("#lxc_ha_state_value", Label).update(ha_state_str)
        self.query_one("#lxc_node_value", Label).update(
            node.get("node", "N/A"))
        self.query_one("#lxc_tags_value", Label).update(
            node.get("tags", ""))
        self.query_one("#lxc_unprivileged_value", Label).update("Yes" if status_current.get(
            "unprivileged", 1) == 1 else "No")
        self.query_one("#lxc_cpu_bar", ProgressBar).update(progress=cpu_usage)
        self.query_one("#lxc_memory_bar", ProgressBar).update(
            progress=memory_usage)
        self.query_one("#lxc_swap_bar", ProgressBar).update(
            progress=swap_usage)
        self.query_one("#lxc_boot_disk_bar", ProgressBar).update(
            progress=boot_disk_usage)
