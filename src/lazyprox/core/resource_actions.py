from textual.widgets import DataTable

from lazyprox.data import ProxmoxData

from .cluster_state import online_node_names, snapshot_nodes
from .guest_operations import perform_guest_operation


class ResourceActions:
    def __init__(self, event: DataTable.RowSelected):
        self.actions: dict = {
            "node": {
                "online": [
                    "Shutdown",
                    "Reboot",
                    "SSH",
                ],
                "offline": [
                    "Start",
                ],
            },
            "lxc": {
                "running": [
                    "Shutdown",
                    "Reboot",
                    "Stop",
                    "SSH",
                ],
                "stopped": [
                    "Start",
                ],
            },
            "qemu": {
                "running": [
                    "Shutdown",
                    "Reboot",
                    "Hibernate",
                    "Stop",
                    "Reset",
                    "SSH",
                ],
                "stopped": [
                    "Start",
                ],
            },
        }
        self.event = event

    def _get_row(self) -> list:
        return self.event.data_table.get_row(self.event.row_key)

    def _get_status(self, resource_type: str) -> str:

        if resource_type == "node":
            return self._get_row()[1]
        if resource_type == "lxc" or resource_type == "qemu":
            return self._get_row()[2]

        raise TypeError(f"Unknown DataTable type: {type}")

    def _online_nodes(self) -> list[str]:
        return online_node_names(snapshot_nodes())

    def _migration_available(self, resource_type: str, status: str) -> bool:
        if resource_type not in {"lxc", "qemu"} or status not in {"running", "stopped"}:
            return False
        online = self._online_nodes()
        return len(online) >= 2 and self._get_row()[-1] in online

    def get_actions_list(self) -> list[str | None]:
        resource_type = self.event.data_table.table_type
        status = self._get_status(resource_type)
        actions = list(self.actions.get(resource_type).get(status, []))
        if self._migration_available(resource_type, status):
            actions.append("Migrate")
        return actions

    def get_migration_targets(self) -> list[str]:
        source = self._get_row()[-1]
        return [name for name in self._online_nodes() if name != source]

    def get_resource_name(self) -> str:
        return self._get_row()[0]

    def get_confirm_message(self, action: str, target: str | None = None) -> str:
        resource_type = self.event.data_table.table_type
        name = self.get_resource_name()
        action_lower = action.lower()

        if resource_type == "node":
            return f"Are you sure you want to {action_lower} node {name}?"

        row = self._get_row()
        vmid = row[1]
        label = "LXC" if resource_type == "lxc" else "VM"
        if action_lower == "migrate":
            return f"Are you sure you want to migrate {label} {vmid} ({name}) from {row[-1]} to {target}?"
        return f"Are you sure you want to {action_lower} {label} {vmid} ({name})?"

    def perform_action(self, selected_action: str, target: str | None = None) -> None:
        action = selected_action.lower()
        resource_type = self.event.data_table.table_type
        row = self._get_row()
        node = row[-1]
        name = row[0]
        vmid = row[1]

        if resource_type in {"lxc", "qemu"}:
            perform_guest_operation(
                ProxmoxData.prox,
                node=node,
                vmid=vmid,
                guest_type=resource_type,
                status=row[2],
                operation=action,
                target=target,
            )
            return
        if resource_type == "node":
            ProxmoxData.prox.nodes(name).status().post(command=action)
