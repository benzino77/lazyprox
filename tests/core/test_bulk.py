from unittest.mock import MagicMock, patch

import pytest

from lazyprox.core.bulk import (
    BulkGuest,
    confirmation_message,
    dispatch_bulk,
    eligible_guests,
    first_operation,
    offerable_operations,
    row_prompt,
    vmid_column_width,
)
from lazyprox.core.cluster_state import NodeState, snapshot_nodes
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


TWO_ONLINE = [NodeState("pve1", "online"), NodeState("pve2", "online")]
ONE_ONLINE = [NodeState("pve1", "online"), NodeState("pve2", "offline")]


def test_offerable_operations_keep_only_operations_with_eligible_guests():
    assert offerable_operations(MIXED, TWO_ONLINE) == ("start", "shutdown", "migrate")
    assert offerable_operations(MIXED, ONE_ONLINE) == ("start", "shutdown")

    stopped_only = [guest(100), guest(101, guest_type="lxc")]
    assert offerable_operations(stopped_only, TWO_ONLINE) == ("start", "migrate")
    assert offerable_operations(stopped_only, ONE_ONLINE) == ("start",)

    running_only = [guest(200, status="running"), guest(201, status="running", guest_type="lxc")]
    assert offerable_operations(running_only, TWO_ONLINE) == ("shutdown", "migrate")
    assert offerable_operations(running_only, ONE_ONLINE) == ("shutdown",)

    templates_only = [
        guest(300, template=True),
        guest(301, status="running", guest_type="lxc", template=True),
    ]
    assert offerable_operations(templates_only, TWO_ONLINE) == ("migrate",)
    assert offerable_operations(templates_only, ONE_ONLINE) == ()
    assert offerable_operations([], ONE_ONLINE) == ()


def test_first_operation_follows_dialog_order_and_is_none_when_empty():
    assert first_operation(MIXED, ONE_ONLINE) == "start"
    assert first_operation([guest(200, status="running")], ONE_ONLINE) == "shutdown"
    assert first_operation([guest(300, template=True)], TWO_ONLINE) == "migrate"
    assert first_operation([guest(300, template=True)], ONE_ONLINE) is None
    assert first_operation([], []) is None


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


ROW_BUDGET = 65


def test_row_prompt_aligns_columns_across_different_name_lengths():
    guests = [
        guest(100, name="db", node="pve1"),
        guest(101, name="web-frontend-eu-west", guest_type="lxc", node="pve2"),
        guest(200, name="cache", status="running", node="pve1"),
    ]
    vmid_width = vmid_column_width(guests)
    rows = [(row_prompt(row, include_node=True, vmid_width=vmid_width), row) for row in guests]

    columns = {
        (
            prompt.index(row.name),
            prompt.index("LXC" if row.guest_type == "lxc" else "VM"),
            prompt.index(row.node),
            prompt.index(row.status),
        )
        for prompt, row in rows
    }
    assert len(columns) == 1
    assert all(len(prompt) <= ROW_BUDGET for prompt, _ in rows)


def test_row_prompt_truncates_long_guest_name_to_its_column():
    long_name = "guest-name-" + "x" * 40
    prompt = row_prompt(guest(100, name=long_name, node="pve1"), include_node=True, vmid_width=6)

    columns = prompt.split()
    assert columns[0] == "100"
    assert columns[1].endswith("…")
    assert len(columns[1]) == 29
    assert long_name not in prompt
    assert columns[2:] == ["VM", "pve1", "stopped"]
    assert len(prompt) <= ROW_BUDGET


def test_row_prompt_truncates_long_node_name_to_its_column():
    long_node = "node-" + "y" * 30
    prompt = row_prompt(guest(100, name="db", node=long_node), include_node=True, vmid_width=6)

    columns = prompt.split()
    assert columns[1] == "db"
    assert columns[3].endswith("…")
    assert len(columns[3]) == 16
    assert long_node not in prompt
    assert columns[4] == "stopped"
    assert len(prompt) <= ROW_BUDGET


def test_row_prompt_migrate_rows_omit_node_and_stay_aligned():
    guests = [
        guest(100, name="db", node="pve1"),
        guest(101, name="web-frontend-eu-west", guest_type="lxc", node="pve1"),
    ]
    vmid_width = vmid_column_width(guests)
    rows = [(row_prompt(row, include_node=False, vmid_width=vmid_width), row) for row in guests]

    assert all(row.node not in prompt for prompt, row in rows)
    assert all(len(prompt.split()) == 4 for prompt, _ in rows)
    columns = {
        (
            prompt.index(row.name),
            prompt.index("LXC" if row.guest_type == "lxc" else "VM"),
            prompt.index(row.status),
        )
        for prompt, row in rows
    }
    assert len(columns) == 1
    assert all(len(prompt) <= ROW_BUDGET for prompt, _ in rows)


def test_row_prompt_fits_the_budget_for_extreme_values():
    extreme = guest(999999999, name="n" * 80, status="suspended", node="h" * 80)
    vmid_width = vmid_column_width([extreme])

    for include_node in (True, False):
        prompt = row_prompt(extreme, include_node=include_node, vmid_width=vmid_width)
        assert len(prompt) <= ROW_BUDGET
        assert str(extreme.vmid) in prompt
        assert "…" in prompt


def test_vmid_column_width_tracks_the_widest_vmid():
    assert vmid_column_width([]) == 6
    assert vmid_column_width([guest(100)]) == 6
    assert vmid_column_width([guest(100), guest(1000000)]) == 7
    assert vmid_column_width([guest(100), guest(999999999)]) == 9


def test_wide_vmid_keeps_rows_at_the_budget_width():
    guests = [
        guest(100, name="db", node="pve1"),
        guest(1000000, name="big-db", status="running", node="pve1"),
    ]
    vmid_width = vmid_column_width(guests)
    assert vmid_width == 7

    for row in guests:
        prompt = row_prompt(row, include_node=True, vmid_width=vmid_width)
        assert str(row.vmid) in prompt
        assert len(prompt) <= ROW_BUDGET


def test_truncated_row_still_exposes_guest_identity():
    longname = guest(100, name="a" * 60, guest_type="lxc", node="pve1")
    prompt = row_prompt(longname, include_node=True, vmid_width=vmid_column_width([longname]))

    assert str(longname.vmid) in prompt
    assert "LXC" in prompt
