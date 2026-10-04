from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from lazyprox.data import ProxmoxData

from .cluster_state import NodeState, online_node_names, snapshot_nodes
from .guest_operations import perform_guest_operation

Operation = Literal["start", "shutdown", "migrate"]
GuestType = Literal["lxc", "qemu"]
GuestKey = tuple[GuestType, int]

_OPERATION_LABEL = {"start": "Start", "shutdown": "Shutdown", "migrate": "Migrate"}


@dataclass(frozen=True)
class BulkGuest:
    vmid: int
    name: str
    status: str
    guest_type: GuestType
    node: str
    template: bool = False

    @classmethod
    def from_api(cls, raw: dict, guest_type: GuestType) -> "BulkGuest":
        template = raw.get("template", 0)
        vmid = int(raw["vmid"])
        return cls(
            vmid=vmid,
            name=str(raw.get("name") or vmid),
            status=str(raw.get("status", "")),
            guest_type=guest_type,
            node=str(raw["node"]),
            template=template in (1, True, "1"),
        )


@dataclass(frozen=True)
class BulkState:
    operation: Operation
    checked: frozenset[GuestKey]
    source: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class BulkSubmission:
    operation: Operation
    guests: tuple[BulkGuest, ...]
    source: str | None
    target: str | None
    message: str

    def as_state(self) -> BulkState:
        return BulkState(
            operation=self.operation,
            checked=frozenset((guest.guest_type, guest.vmid) for guest in self.guests),
            source=self.source,
            target=self.target,
        )


@dataclass(frozen=True)
class BulkSummary:
    operation: Operation
    requested: int
    failed: int

    @property
    def message(self) -> str:
        return summary_message(self.operation, self.requested, self.failed)


def migrate_available(nodes: Sequence[NodeState]) -> bool:
    return len(online_node_names(nodes)) >= 2


def type_label(guest_type: GuestType) -> str:
    return "VM" if guest_type == "qemu" else "LXC"


# Bulk guest rows must fit the SelectionList label area. The dialog is 80 columns
# wide; its round border (2) and padding (2) leave 76. The SelectionList adds a
# tall border (2) and horizontal padding (2), leaving 72, and its selection button
# takes 4 more. Reserving the 2-cell vertical scrollbar plus one blank column
# before it keeps rows clear of the scrollbar, so formatted rows target 65 columns.
_ELLIPSIS = "…"
_VMID_MIN_WIDTH = 6
_VMID_MAX_WIDTH = 9
_NAME_WIDTH = 29
_TYPE_WIDTH = 3
_NODE_WIDTH = 16
_STATUS_WIDTH = 7


def vmid_column_width(guests: Sequence[BulkGuest]) -> int:
    """Widest VMID in the list, clamped to the column's minimum and maximum."""
    widest = max((len(str(guest.vmid)) for guest in guests), default=_VMID_MIN_WIDTH)
    return min(_VMID_MAX_WIDTH, max(_VMID_MIN_WIDTH, widest))


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return f"{text[: width - 1]}{_ELLIPSIS}"


def _fit(text: str, width: int) -> str:
    return _truncate(text, width).ljust(width)


def row_prompt(guest: BulkGuest, *, include_node: bool, vmid_width: int = _VMID_MIN_WIDTH) -> str:
    name_width = _NAME_WIDTH - (vmid_width - _VMID_MIN_WIDTH)
    columns = [
        str(guest.vmid).rjust(vmid_width),
        _fit(guest.name, name_width),
        _fit(type_label(guest.guest_type), _TYPE_WIDTH),
    ]
    if include_node:
        columns.append(_fit(guest.node, _NODE_WIDTH))
    columns.append(_truncate(guest.status, _STATUS_WIDTH))
    return " ".join(columns).rstrip()


def eligible_guests(
    guests: Sequence[BulkGuest],
    operation: Operation,
    source: str | None = None,
) -> list[BulkGuest]:
    if operation == "start":
        selected = [guest for guest in guests if not guest.template and guest.status == "stopped"]
        return sorted(selected, key=lambda guest: (guest.node, guest.guest_type, guest.vmid))
    if operation == "shutdown":
        selected = [guest for guest in guests if not guest.template and guest.status == "running"]
        return sorted(selected, key=lambda guest: (guest.node, guest.guest_type, guest.vmid))
    if not source:
        return []
    selected = [
        guest
        for guest in guests
        if not guest.template and guest.node == source and guest.status in {"running", "stopped"}
    ]
    return sorted(selected, key=lambda guest: (guest.guest_type, guest.vmid))


def _guest_word(count: int) -> str:
    return "guest" if count == 1 else "guests"


def type_counts(guests: Sequence[BulkGuest]) -> str:
    vms = sum(1 for guest in guests if guest.guest_type == "qemu")
    lxcs = sum(1 for guest in guests if guest.guest_type == "lxc")
    parts: list[str] = []
    if vms:
        parts.append(f"{vms} VM" if vms == 1 else f"{vms} VMs")
    if lxcs:
        parts.append(f"{lxcs} LXC")
    return ", ".join(parts)


def confirmation_message(
    operation: Operation,
    guests: Sequence[BulkGuest],
    source: str | None = None,
    target: str | None = None,
) -> str:
    count = len(guests)
    word = _guest_word(count)
    counts = type_counts(guests)
    if operation == "start":
        return f"Start {count} {word} ({counts})?"
    if operation == "shutdown":
        return f"Shut down {count} {word} ({counts})?"
    return f"Migrate {count} {word} from {source} to {target} ({counts})?"


def summary_message(operation: Operation, requested: int, failed: int) -> str:
    label = _OPERATION_LABEL[operation]
    word = _guest_word(requested)
    if failed:
        return f"{label} requested for {requested} {word}, {failed} failed"
    return f"{label} requested for {requested} {word}"


def snapshot_guests() -> tuple[list[NodeState], list[BulkGuest]]:
    nodes = snapshot_nodes()
    guests: list[BulkGuest] = []
    for guest_type in ("lxc", "qemu"):
        for raw in ProxmoxData.get_guests_list(guest_type):
            guests.append(BulkGuest.from_api(raw, guest_type))
    return nodes, guests


def dispatch_bulk(
    guests: Sequence[BulkGuest],
    operation: Operation,
    *,
    target: str | None = None,
    prox=None,
) -> BulkSummary:
    if operation == "migrate" and not target:
        raise ValueError("migrate target is required")
    api = ProxmoxData.prox if prox is None else prox
    requested = 0
    failed = 0
    for guest in guests:
        try:
            perform_guest_operation(
                api,
                node=guest.node,
                vmid=guest.vmid,
                guest_type=guest.guest_type,
                status=guest.status,
                operation=operation,
                target=target,
            )
        except Exception:  # noqa: BLE001
            failed += 1
        else:
            requested += 1
    return BulkSummary(operation=operation, requested=requested, failed=failed)
