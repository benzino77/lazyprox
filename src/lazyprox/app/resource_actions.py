from textual.widgets import DataTable

from lazyprox.data import ProxmoxData


class ResourceActions:

    def __init__(self, event: DataTable.RowSelected):
        self.actions: dict = {
            "node": {
                "online": ["Shutdown", "Reboot", "SSH",],
                "offline": ["Start",]
            },
            "lxc": {
                "running": ["Shutdown", "Reboot", "Stop", "SSH",],
                "stopped": ["Start",]
            },
            "qemu": {
                "running": ["Shutdown", "Reboot", "Hibernate", "Stop", "Reset", "SSH",],
                "stopped": ["Start",]
            }
        }
        self.event = event

    def _get_status(self, resource_type: str) -> str:

        if resource_type == "node":
            return self.event.data_table.get_row(self.event.row_key)[1]
        if resource_type == "lxc" or resource_type == "qemu":
            return self.event.data_table.get_row(self.event.row_key)[2]

        raise TypeError(f"Unknown DataTable type: {type}")

    def get_actions_list(self) -> list[str | None]:
        resource_type = self.event.data_table.table_type
        status = self._get_status(resource_type)

        return self.actions.get(resource_type).get(status, [])

    def get_resource_name(self) -> str:
        return self.event.data_table.get_row(self.event.row_key)[0]

    def perform_action(self, selected_action: str) -> None:
        action = selected_action.lower()
        resource_type = self.event.data_table.table_type
        node = self.event.data_table.get_row(self.event.row_key)[-1]
        name = self.event.data_table.get_row(self.event.row_key)[0]
        vmid = self.event.data_table.get_row(self.event.row_key)[1]

        if resource_type == "lxc":
            ProxmoxData.prox.nodes(node).lxc(vmid).status.post(action)
        if resource_type == "qemu":
            # hibernate action in fact is named "suspend" and needs to pass parameter "todisk"
            if action == "hibernate":
                ProxmoxData.prox.nodes(node).qemu(
                    vmid).status.post("suspend", todisk=1)
            else:
                ProxmoxData.prox.nodes(node).qemu(vmid).status.post(action)
        if resource_type == "node":
            ProxmoxData.prox.nodes(name).status().post(command=action)
