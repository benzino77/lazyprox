from unittest.mock import MagicMock, patch

import pytest

from lazyprox.core.bulk import (
    BulkGuest,
    confirmation_message,
    dispatch_bulk,
    eligible_guests,
)
from lazyprox.core.cluster_state import snapshot_nodes
from lazyprox.data import ProxmoxData


def guest(
    vmid: int,
    *,
    name: str | None = None,
    status: str = "stopped",
    guest_type: str = "qemu",
    node: str = "pve1",
    template: bool = False,
) -> BulkGuest:
    return BulkGuest(
        vmid=vmid,
        name=name or f"guest-{vmid}",
        status=status,
        guest_type=guest_type,
        node=node,
        template=template,
    )


MIXED = [
    guest(101, name="web", status="stopped", guest_type="lxc", node="pve2"),
    guest(100, name="db", status="stopped", guest_type="qemu", node="pve1"),
    guest(200, name="app", status="running", guest_type="qemu", node="pve1"),
    guest(102, name="cache", status="running", guest_type="lxc", node="pve2"),
    guest(300, name="paused-vm", status="paused", guest_type="qemu", node="pve1"),
    guest(301, name="template", status="stopped", guest_type="qemu", node="pve1", template=True),
    guest(302, name="template-ct", status="running", guest_type="lxc", node="pve2", template=True),
    guest(400, name="other-node", status="stopped", guest_type="lxc", node="pve3"),
]


def test_start_lists_mixed_stopped_guests_and_excludes_the_rest():
    rows = eligible_guests(MIXED, "start")

    assert [(row.guest_type, row.vmid, row.node) for row in rows] == [
        ("qemu", 100, "pve1"),
        ("lxc", 101, "pve2"),
        ("lxc", 400, "pve3"),
    ]
    assert all(row.status == "stopped" for row in rows)
    assert all(not row.template for row in rows)
    assert "paused" not in {row.status for row in rows}


def test_shutdown_lists_only_running_guests():
    rows = eligible_guests(MIXED, "shutdown")

    assert [(row.guest_type, row.vmid) for row in rows] == [("qemu", 200), ("lxc", 102)]
    assert all(row.status == "running" for row in rows)
    assert all(not row.template for row in rows)


def test_migrate_is_limited_to_the_source_node():
    rows = eligible_guests(MIXED, "migrate", source="pve1")

    assert {row.node for row in rows} == {"pve1"}
    assert [(row.guest_type, row.vmid) for row in rows] == [("qemu", 100), ("qemu", 200)]
    assert all(row.vmid != 300 for row in rows)
    assert all(not row.template for row in rows)
    assert eligible_guests(MIXED, "migrate", source=None) == []


@pytest.mark.parametrize(
    ("operation", "guests", "source", "target", "expected"),
    [
        ("start", [guest(1, guest_type="qemu")], None, None, "Start 1 guest (1 VM)?"),
        (
            "shutdown",
            [guest(index, guest_type="qemu", status="running") for index in range(5)]
            + [guest(index, guest_type="lxc", status="running") for index in range(10, 13)],
            None,
            None,
            "Shut down 8 guests (5 VMs, 3 LXC)?",
        ),
        (
            "migrate",
            [guest(1, guest_type="qemu")],
            "pve1",
            "pve2",
            "Migrate 1 guest from pve1 to pve2 (1 VM)?",
        ),
    ],
)
def test_confirmation_message(operation, guests, source, target, expected):
    assert confirmation_message(operation, guests, source, target) == expected


def test_shutdown_posts_shutdown_not_stop():
    prox = MagicMock()
    guests = [guest(100, status="running", guest_type="lxc"), guest(200, status="running", guest_type="qemu")]

    summary = dispatch_bulk(guests, "shutdown", prox=prox)

    lxc_post = prox.nodes.return_value.lxc.return_value.status.post
    qemu_post = prox.nodes.return_value.qemu.return_value.status.post
    lxc_post.assert_called_once_with("shutdown")
    qemu_post.assert_called_once_with("shutdown")
    assert ("stop",) not in lxc_post.call_args_list and ("stop",) not in qemu_post.call_args_list
    assert summary.requested == 2
    assert summary.failed == 0
    assert summary.message == "Shutdown requested for 2 guests"
    assert "have shut down" not in summary.message


def test_dispatch_continues_after_a_failure_and_reports_both_counts():
    prox = MagicMock()
    calls = {"n": 0}

    def side_effect(action):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("nope")
        return "UPID:ok"

    prox.nodes.return_value.lxc.return_value.status.post.side_effect = side_effect
    guests = [guest(100, status="running", guest_type="lxc"), guest(101, status="running", guest_type="lxc")]

    summary = dispatch_bulk(guests, "shutdown", prox=prox)

    assert prox.nodes.return_value.lxc.return_value.status.post.call_count == 2
    assert summary.requested == 1
    assert summary.failed == 1
    assert summary.message == "Shutdown requested for 1 guest, 1 failed"
    assert summary.message != "Shutdown requested for 2 guests"


def test_running_qemu_migrate_is_online_with_local_disks():
    prox = MagicMock()
    dispatch_bulk(
        [guest(100, status="running", guest_type="qemu", node="pve1")],
        "migrate",
        target="pve2",
        prox=prox,
    )
    post = prox.nodes.return_value.qemu.return_value.migrate.post
    post.assert_called_once_with(target="pve2", online=1, **{"with-local-disks": 1})
    assert post.call_args.kwargs["with-local-disks"] == 1


def test_running_lxc_migrate_uses_restart_mode():
    prox = MagicMock()
    dispatch_bulk(
        [guest(101, status="running", guest_type="lxc", node="pve1")],
        "migrate",
        target="pve2",
        prox=prox,
    )
    post = prox.nodes.return_value.lxc.return_value.migrate.post
    post.assert_called_once_with(target="pve2", restart=1)
    assert "online" not in post.call_args.kwargs
    assert "with-local-disks" not in post.call_args.kwargs


def test_stopped_migrate_omits_online_and_restart():
    prox = MagicMock()
    dispatch_bulk(
        [guest(102, status="stopped", guest_type="lxc", node="pve1")],
        "migrate",
        target="pve2",
        prox=prox,
    )
    post = prox.nodes.return_value.lxc.return_value.migrate.post
    post.assert_called_once_with(target="pve2")
    assert "online" not in post.call_args.kwargs
    assert "restart" not in post.call_args.kwargs

    qemu_prox = MagicMock()
    dispatch_bulk(
        [guest(103, status="stopped", guest_type="qemu", node="pve1")],
        "migrate",
        target="pve2",
        prox=qemu_prox,
    )
    qemu_post = qemu_prox.nodes.return_value.qemu.return_value.migrate.post
    qemu_post.assert_called_once_with(target="pve2")
    assert "with-local-disks" not in qemu_post.call_args.kwargs


def test_snapshot_nodes_reads_node_name_and_status():
    resources = {
        "nodes": [
            {"node": "pve1", "status": "online"},
            {"node": "pve2", "status": "offline"},
        ]
    }
    with patch.object(ProxmoxData, "p_prox_resources", resources):
        nodes = snapshot_nodes()

    assert [(node.name, node.status) for node in nodes] == [("pve1", "online"), ("pve2", "offline")]
