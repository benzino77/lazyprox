from unittest.mock import MagicMock, patch

from lazyprox.core.cluster_state import NodeState
from lazyprox.core.resource_actions import ResourceActions
from lazyprox.data import ProxmoxData

LXC_RUNNING = ["web", "101", "running", "50%", "50%", "pve1"]
LXC_STOPPED = ["web", "101", "stopped", "0.0%", "0.0%", "pve1"]
QEMU_RUNNING = ["db", "100", "running", "10.0%", "1.0%", "pve1"]
QEMU_STOPPED = ["db", "100", "stopped", "0.0%", "0.0%", "pve1"]
QEMU_PAUSED = ["db", "100", "paused", "10.0%", "1.0%", "pve1"]
NODE_ROW = ["pve1", "online", "50%", "50%"]

TWO_ONLINE = [NodeState("pve1", "online"), NodeState("pve2", "online")]
ONE_ONLINE = [NodeState("pve1", "online"), NodeState("pve2", "offline")]
SOURCE_OFFLINE = [NodeState("pve1", "offline"), NodeState("pve2", "online"), NodeState("pve3", "online")]
SOURCE_PLUS_ONLINE_AND_OFFLINE = [
    NodeState("pve1", "online"),
    NodeState("pve2", "online"),
    NodeState("pve3", "offline"),
]


def make_actions(table_type: str, row: list) -> ResourceActions:
    event = MagicMock()
    event.row_key = "key"
    event.data_table.table_type = table_type
    event.data_table.get_row.return_value = row
    return ResourceActions(event)


def test_running_lxc_with_two_online_nodes_offers_migrate():
    actions = make_actions("lxc", LXC_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        result = actions.get_actions_list()

    assert result == ["Shutdown", "Reboot", "Stop", "SSH", "Migrate"]


def test_running_qemu_with_two_online_nodes_offers_migrate():
    actions = make_actions("qemu", QEMU_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        result = actions.get_actions_list()

    assert result == ["Shutdown", "Reboot", "Hibernate", "Stop", "Reset", "SSH", "Migrate"]


def test_stopped_guest_offers_start_and_migrate():
    actions = make_actions("lxc", LXC_STOPPED)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        result = actions.get_actions_list()

    assert result == ["Start", "Migrate"]


def test_single_online_node_hides_migrate():
    actions = make_actions("lxc", LXC_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=ONE_ONLINE):
        result = actions.get_actions_list()

    assert "Migrate" not in result


def test_offline_source_node_hides_migrate():
    actions = make_actions("lxc", LXC_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=SOURCE_OFFLINE):
        result = actions.get_actions_list()

    assert "Migrate" not in result


def test_other_guest_status_hides_migrate():
    actions = make_actions("qemu", QEMU_PAUSED)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        result = actions.get_actions_list()

    assert result == []


def test_node_actions_do_not_offer_migrate():
    actions = make_actions("node", NODE_ROW)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        result = actions.get_actions_list()

    assert result == ["Shutdown", "Reboot", "SSH"]


def test_migrate_is_not_persisted_into_the_static_action_map():
    actions = make_actions("lxc", LXC_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=TWO_ONLINE):
        first = actions.get_actions_list()
        second = actions.get_actions_list()

    assert first == second
    assert actions.actions["lxc"]["running"] == ["Shutdown", "Reboot", "Stop", "SSH"]


def test_migration_targets_exclude_source_and_offline_nodes():
    actions = make_actions("lxc", LXC_RUNNING)

    with patch("lazyprox.core.resource_actions.snapshot_nodes", return_value=SOURCE_PLUS_ONLINE_AND_OFFLINE):
        targets = actions.get_migration_targets()

    assert targets == ["pve2"]


def test_migrate_confirm_message_names_guest_source_and_target():
    lxc = make_actions("lxc", LXC_RUNNING)
    qemu = make_actions("qemu", QEMU_STOPPED)

    assert (
        lxc.get_confirm_message("Migrate", target="pve2")
        == "Are you sure you want to migrate LXC 101 (web) from pve1 to pve2?"
    )
    assert (
        qemu.get_confirm_message("Migrate", target="pve2")
        == "Are you sure you want to migrate VM 100 (db) from pve1 to pve2?"
    )


def test_non_migrate_confirm_messages_are_unchanged():
    lxc = make_actions("lxc", LXC_RUNNING)
    qemu = make_actions("qemu", QEMU_STOPPED)
    node = make_actions("node", NODE_ROW)

    assert lxc.get_confirm_message("Shutdown") == "Are you sure you want to shutdown LXC 101 (web)?"
    assert qemu.get_confirm_message("Start") == "Are you sure you want to start VM 100 (db)?"
    assert node.get_confirm_message("Reboot") == "Are you sure you want to reboot node pve1?"


def test_perform_action_delegates_lxc_migrate_to_shared_layer():
    actions = make_actions("lxc", LXC_RUNNING)
    prox = MagicMock()

    with (
        patch.object(ProxmoxData, "prox", prox, create=True),
        patch("lazyprox.core.resource_actions.perform_guest_operation") as operation,
    ):
        actions.perform_action("Migrate", target="pve2")
        operation.assert_called_once_with(
            prox,
            node="pve1",
            vmid="101",
            guest_type="lxc",
            status="running",
            operation="migrate",
            target="pve2",
        )


def test_perform_action_delegates_qemu_start_to_shared_layer():
    actions = make_actions("qemu", QEMU_STOPPED)
    prox = MagicMock()

    with (
        patch.object(ProxmoxData, "prox", prox, create=True),
        patch("lazyprox.core.resource_actions.perform_guest_operation") as operation,
    ):
        actions.perform_action("Start")
        operation.assert_called_once_with(
            prox,
            node="pve1",
            vmid="100",
            guest_type="qemu",
            status="stopped",
            operation="start",
            target=None,
        )


def test_perform_action_node_still_posts_to_node_status_endpoint():
    actions = make_actions("node", NODE_ROW)
    prox = MagicMock()

    with patch.object(ProxmoxData, "prox", prox, create=True):
        actions.perform_action("Shutdown")

    prox.nodes.assert_called_once_with("pve1")
    prox.nodes.return_value.status.return_value.post.assert_called_once_with(command="shutdown")
