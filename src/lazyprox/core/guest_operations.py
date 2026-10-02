from typing import Literal

GuestType = Literal["lxc", "qemu"]
GuestOperation = Literal["start", "shutdown", "reboot", "stop", "reset", "hibernate", "migrate"]


def perform_guest_operation(
    prox,
    *,
    node: str,
    vmid: int | str,
    guest_type: GuestType,
    status: str,
    operation: GuestOperation,
    target: str | None = None,
) -> None:
    """Send one Proxmox request for a single guest operation.

    Raises on failure so the caller decides whether to stop (single-guest flow)
    or continue with the remaining guests (bulk dispatch).
    """
    node_api = prox.nodes(node)
    guest_api = node_api.lxc(vmid) if guest_type == "lxc" else node_api.qemu(vmid)

    if operation == "migrate":
        if not target:
            raise ValueError("migrate target is required")
        if status == "running":
            if guest_type == "lxc":
                # container live migration is not implemented, so restart mode is used
                guest_api.migrate.post(target=target, restart=1)
            else:
                guest_api.migrate.post(target=target, online=1, **{"with-local-disks": 1})
            return
        guest_api.migrate.post(target=target)
        return

    # hibernate action in fact is named "suspend" and needs parameter "todisk"
    if operation == "hibernate":
        guest_api.status.post("suspend", todisk=1)
        return

    guest_api.status.post(operation)
