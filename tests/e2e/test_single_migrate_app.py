from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Select

from lazyprox.app import LazyProx
from lazyprox.data import ProxmoxData
from lazyprox.screens import (
    ActionSelectionScreen,
    ConfirmationScreen,
    DashboardScreen,
    DestinationSelectionScreen,
)
from lazyprox.widgets import LxcWidget

pytestmark = pytest.mark.e2e

RESOURCES = {
    "nodes": [
        {"node": "pve1", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
        {"node": "pve2", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
        {"node": "pve3", "status": "offline", "mem": 1, "maxmem": 2, "cpu": 0.1},
    ],
    "nodes/pve1/status": {},
    "nodes/pve2/status": {},
    "nodes/pve3/status": {},
    "nodes/pve1/lxc": [{"vmid": 101, "name": "web", "status": "running", "template": 0}],
    "nodes/pve1/qemu": [],
    "nodes/pve2/lxc": [],
    "nodes/pve2/qemu": [],
    "nodes/pve3/lxc": [],
    "nodes/pve3/qemu": [],
    "nodes/pve1/lxc/101/status/current": {"mem": 1, "maxmem": 2, "cpu": 0.1},
}


def dashboard_mount(self) -> None:
    self.push_screen("dashboard")


@pytest.fixture
def seeded_proxmox():
    previous = ProxmoxData.p_prox_resources
    ProxmoxData.p_prox_resources = RESOURCES
    yield
    ProxmoxData.p_prox_resources = previous


async def wait_for_type(pilot, screen_type):
    for _ in range(50):
        if isinstance(pilot.app.screen, screen_type):
            await pilot.pause()
            return
        await pilot.pause()
    raise AssertionError(f"Expected {screen_type.__name__}, got {type(pilot.app.screen).__name__}")


async def open_lxc_action_menu(pilot, app) -> None:
    lxc_widget = app.screen.query_one(LxcWidget)
    lxc_widget.update_table_data()
    lxc_widget.move_cursor(row=0)
    app.screen.set_focus(lxc_widget)
    await pilot.pause()
    await pilot.press("enter")
    await wait_for_type(pilot, ActionSelectionScreen)


async def choose_migrate_destination(pilot, app, target: str) -> None:
    app.screen.query_one("#action_select", Select).value = "Migrate"
    await wait_for_type(pilot, DestinationSelectionScreen)
    app.screen.query_one("#destination_select", Select).value = target
    await wait_for_type(pilot, ConfirmationScreen)


async def test_destination_cancel_sends_no_request(seeded_proxmox):
    app = LazyProx()
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch("lazyprox.core.resource_actions.perform_guest_operation") as operation,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await open_lxc_action_menu(pilot, app)
            app.screen.query_one("#action_select", Select).value = "Migrate"
            await wait_for_type(pilot, DestinationSelectionScreen)

            destination_select = app.screen.query_one("#destination_select", Select)
            choices = [value for _, value in destination_select._options if value is not Select.NULL]
            assert choices == ["pve2"]

            await pilot.press("escape")
            await wait_for_type(pilot, DashboardScreen)
            operation.assert_not_called()
            assert not any(isinstance(screen, ConfirmationScreen) for screen in app.screen_stack)


async def test_confirmation_no_sends_no_request(seeded_proxmox):
    app = LazyProx()
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch("lazyprox.core.resource_actions.perform_guest_operation") as operation,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await open_lxc_action_menu(pilot, app)
            await choose_migrate_destination(pilot, app, "pve2")

            assert app.screen.question == "Are you sure you want to migrate LXC 101 (web) from pve1 to pve2?"
            await pilot.click("#confirm_no")
            await wait_for_type(pilot, DashboardScreen)
            operation.assert_not_called()


async def test_confirmed_migrate_dispatches_with_target_and_notifies(seeded_proxmox):
    app = LazyProx()
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch.object(ProxmoxData, "prox", MagicMock(), create=True),
        patch("lazyprox.core.resource_actions.perform_guest_operation") as operation,
        patch.object(app, "notify") as notify,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await open_lxc_action_menu(pilot, app)
            await choose_migrate_destination(pilot, app, "pve2")
            await pilot.click("#confirm_yes")

            for _ in range(50):
                if operation.called and notify.called:
                    break
                await pilot.pause()
            else:
                raise AssertionError("Migration was not dispatched")

            assert operation.call_args.kwargs["node"] == "pve1"
            assert operation.call_args.kwargs["guest_type"] == "lxc"
            assert operation.call_args.kwargs["status"] == "running"
            assert operation.call_args.kwargs["operation"] == "migrate"
            assert operation.call_args.kwargs["target"] == "pve2"
            assert notify.call_args.kwargs["message"] == "Migration of web requested"
            assert isinstance(app.screen, DashboardScreen)
