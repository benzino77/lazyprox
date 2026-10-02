from unittest.mock import MagicMock

import pytest

from lazyprox.core.guest_operations import perform_guest_operation


def test_start_posts_status_operation():
    prox = MagicMock()

    perform_guest_operation(prox, node="pve1", vmid=101, guest_type="lxc", status="stopped", operation="start")

    prox.nodes.return_value.lxc.return_value.status.post.assert_called_once_with("start")


def test_shutdown_posts_shutdown_not_stop():
    prox = MagicMock()

    perform_guest_operation(prox, node="pve1", vmid=100, guest_type="qemu", status="running", operation="shutdown")

    qemu_post = prox.nodes.return_value.qemu.return_value.status.post
    qemu_post.assert_called_once_with("shutdown")
    assert ("stop",) not in qemu_post.call_args_list


def test_hibernate_posts_suspend_with_todisk():
    prox = MagicMock()

    perform_guest_operation(prox, node="pve1", vmid=100, guest_type="qemu", status="running", operation="hibernate")

    prox.nodes.return_value.qemu.return_value.status.post.assert_called_once_with("suspend", todisk=1)


def test_reboot_posts_status_operation():
    prox = MagicMock()

    perform_guest_operation(prox, node="pve1", vmid=100, guest_type="qemu", status="running", operation="reboot")

    prox.nodes.return_value.qemu.return_value.status.post.assert_called_once_with("reboot")


def test_running_qemu_migrate_is_online_with_local_disks():
    prox = MagicMock()

    perform_guest_operation(
        prox, node="pve1", vmid=100, guest_type="qemu", status="running", operation="migrate", target="pve2"
    )

    post = prox.nodes.return_value.qemu.return_value.migrate.post
    post.assert_called_once_with(target="pve2", online=1, **{"with-local-disks": 1})
    assert post.call_args.kwargs["with-local-disks"] == 1


def test_running_lxc_migrate_uses_restart_mode():
    prox = MagicMock()

    perform_guest_operation(
        prox, node="pve1", vmid=101, guest_type="lxc", status="running", operation="migrate", target="pve2"
    )

    post = prox.nodes.return_value.lxc.return_value.migrate.post
    post.assert_called_once_with(target="pve2", restart=1)
    assert "online" not in post.call_args.kwargs
    assert "with-local-disks" not in post.call_args.kwargs


@pytest.mark.parametrize("guest_type", ["lxc", "qemu"])
def test_stopped_migrate_omits_online_and_restart(guest_type):
    prox = MagicMock()

    perform_guest_operation(
        prox, node="pve1", vmid=100, guest_type=guest_type, status="stopped", operation="migrate", target="pve2"
    )

    guest_api = prox.nodes.return_value.lxc if guest_type == "lxc" else prox.nodes.return_value.qemu
    post = guest_api.return_value.migrate.post
    post.assert_called_once_with(target="pve2")
    assert "online" not in post.call_args.kwargs
    assert "restart" not in post.call_args.kwargs
    assert "with-local-disks" not in post.call_args.kwargs


def test_migrate_without_target_raises():
    prox = MagicMock()

    with pytest.raises(ValueError, match="migrate target is required"):
        perform_guest_operation(prox, node="pve1", vmid=100, guest_type="qemu", status="stopped", operation="migrate")
